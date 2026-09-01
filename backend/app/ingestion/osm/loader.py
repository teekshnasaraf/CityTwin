import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from .geocoder import ResolvedCity
from .validator import ValidationReport

logger = logging.getLogger("citytwin.ingestion.osm.loader")

BATCH_SIZE = 1000


def get_or_create_osm_data_source(db: Session) -> int:
    """
    Ensures OpenStreetMap is registered in the 'data_sources' table and returns its source_id.
    """
    row = db.execute(
        text("SELECT source_id FROM data_sources WHERE name = :name LIMIT 1;"),
        {"name": "OpenStreetMap"},
    ).fetchone()

    if row:
        return int(row[0])

    insert_row = db.execute(
        text("""
            INSERT INTO data_sources (name, source_type, base_url, description, is_active, created_at, updated_at)
            VALUES (:name, :source_type, :base_url, :description, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING source_id;
        """),
        {
            "name": "OpenStreetMap",
            "source_type": "OSM",
            "base_url": "https://www.openstreetmap.org",
            "description": "OpenStreetMap road network, intersections, and POI data",
        },
    ).fetchone()
    
    return int(insert_row[0])


def upsert_city(db: Session, city: ResolvedCity) -> int:
    """
    Inserts a new city or updates boundary/coordinates if the city already exists (idempotent).
    Returns the persistent city_id.
    """
    row = db.execute(
        text("SELECT city_id FROM cities WHERE LOWER(name) = LOWER(:name) AND LOWER(country) = LOWER(:country) LIMIT 1;"),
        {"name": city.name, "country": city.country},
    ).fetchone()

    boundary_wkt = city.boundary.wkt

    if row:
        city_id = int(row[0])
        db.execute(
            text("""
                UPDATE cities
                SET state = COALESCE(:state, state),
                    latitude = :latitude,
                    longitude = :longitude,
                    boundary = ST_GeomFromText(:boundary_wkt, 4326),
                    updated_at = CURRENT_TIMESTAMP
                WHERE city_id = :city_id;
            """),
            {
                "city_id": city_id,
                "state": city.state,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "boundary_wkt": boundary_wkt,
            },
        )
        logger.info("Updated existing city record (city_id=%d) for '%s, %s'", city_id, city.name, city.country)
        return city_id

    insert_row = db.execute(
        text("""
            INSERT INTO cities (name, country, state, latitude, longitude, boundary, created_at, updated_at)
            VALUES (:name, :country, :state, :latitude, :longitude, ST_GeomFromText(:boundary_wkt, 4326), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING city_id;
        """),
        {
            "name": city.name,
            "country": city.country,
            "state": city.state,
            "latitude": city.latitude,
            "longitude": city.longitude,
            "boundary_wkt": boundary_wkt,
        },
    ).fetchone()

    city_id = int(insert_row[0])
    logger.info("Inserted new city record (city_id=%d) for '%s, %s'", city_id, city.name, city.country)
    return city_id


def save_osm_city_data(
    db: Session,
    city: ResolvedCity,
    roads: List[Dict[str, Any]],
    intersections: List[Dict[str, Any]],
    places: List[Dict[str, Any]],
    quality_reports: List[ValidationReport],
) -> Dict[str, Any]:
    """
    Transactionally loads all validated OSM datasets into PostgreSQL/PostGIS.
    Records comprehensive provenance in ingestion_logs and data_quality_logs.
    """
    source_id = get_or_create_osm_data_source(db)
    city_id = upsert_city(db, city)

    # Patch real city_id into all records (orchestrator uses placeholder during transformation)
    for rec in roads:
        rec["city_id"] = city_id
    for rec in intersections:
        rec["city_id"] = city_id
    for rec in places:
        rec["city_id"] = city_id

    # 1. Create Ingestion Log (IN_PROGRESS)
    log_row = db.execute(
        text("""
            INSERT INTO ingestion_logs (
                source_id, dataset_type, status,
                records_received, records_inserted, records_updated, records_failed,
                error_message, started_at
            ) VALUES (
                :source_id, 'osm_city', 'IN_PROGRESS',
                0, 0, 0, 0, NULL, CURRENT_TIMESTAMP
            ) RETURNING ingestion_id;
        """),
        {"source_id": source_id},
    ).fetchone()
    ingestion_id = int(log_row[0])

    total_processed = len(roads) + len(intersections) + len(places)
    total_inserted = 0

    try:
        # 2. Idempotency: Clean previous entities for this specific city
        db.execute(text("DELETE FROM roads WHERE city_id = :city_id;"), {"city_id": city_id})
        db.execute(text("DELETE FROM intersections WHERE city_id = :city_id;"), {"city_id": city_id})
        db.execute(text("DELETE FROM places WHERE city_id = :city_id;"), {"city_id": city_id})

        # 3. Bulk Insert Intersections
        if intersections:
            stmt_intersections = text("""
                INSERT INTO intersections (city_id, osm_id, geometry, created_at)
                VALUES (:city_id, :osm_id, ST_GeomFromText(:geometry_wkt, 4326), CURRENT_TIMESTAMP);
            """)
            for i in range(0, len(intersections), BATCH_SIZE):
                batch = intersections[i:i + BATCH_SIZE]
                db.execute(stmt_intersections, batch)
            total_inserted += len(intersections)

        # 4. Bulk Insert Roads
        if roads:
            stmt_roads = text("""
                INSERT INTO roads (
                    city_id, osm_id, name, road_type, length_m,
                    speed_limit, lanes, capacity, geometry, created_at, updated_at
                ) VALUES (
                    :city_id, :osm_id, :name, :road_type, :length_m,
                    :speed_limit, :lanes, :capacity, ST_GeomFromText(:geometry_wkt, 4326),
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                );
            """)
            for i in range(0, len(roads), BATCH_SIZE):
                batch = roads[i:i + BATCH_SIZE]
                db.execute(stmt_roads, batch)
            total_inserted += len(roads)

        # 5. Bulk Insert Places
        if places:
            stmt_places = text("""
                INSERT INTO places (city_id, osm_id, name, place_type, geometry, created_at, updated_at)
                VALUES (:city_id, :osm_id, :name, :place_type, ST_GeomFromText(:geometry_wkt, 4326), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """)
            for i in range(0, len(places), BATCH_SIZE):
                batch = places[i:i + BATCH_SIZE]
                db.execute(stmt_places, batch)
            total_inserted += len(places)

        # 6. Record Data Quality Logs
        stmt_quality = text("""
            INSERT INTO data_quality_logs (ingestion_id, table_name, records_checked, records_valid, records_invalid, quality_score, checked_at)
            VALUES (:ingestion_id, :table_name, :records_checked, :records_valid, :records_invalid, :quality_score, CURRENT_TIMESTAMP);
        """)
        for r in quality_reports:
            quality_score = (r.valid_records / r.total_records * 100.0) if r.total_records > 0 else 100.0
            db.execute(
                stmt_quality,
                {
                    "ingestion_id": ingestion_id,
                    "table_name": r.dataset_type,
                    "records_checked": r.total_records,
                    "records_valid": r.valid_records,
                    "records_invalid": r.invalid_records,
                    "quality_score": round(quality_score, 2)
                },
            )

        # 7. Update Ingestion Log to SUCCESS
        db.execute(
            text("""
                UPDATE ingestion_logs
                SET status = 'SUCCESS',
                    records_received = :received,
                    records_inserted = :inserted,
                    records_updated = :updated,
                    records_failed = :failed,
                    completed_at = CURRENT_TIMESTAMP
                WHERE ingestion_id = :ingestion_id;
            """),
            {
                "ingestion_id": ingestion_id,
                "received": total_processed,
                "inserted": total_inserted,
                "updated": 0,
                "failed": total_processed - total_inserted,
            },
        )

        db.commit()
        logger.info("Successfully committed OSM ingestion for %s (city_id=%d, ingestion_id=%d)", city.name, city_id, ingestion_id)

        return {
            "status": "success",
            "city": city.name,
            "city_id": city_id,
            "roads": len(roads),
            "intersections": len(intersections),
            "places": len(places),
            "ingestion_id": ingestion_id,
        }

    except Exception as exc:
        db.rollback()
        logger.error("Failed to load OSM city data into database: %s", str(exc))
        try:
            db.execute(
                text("""
                    UPDATE ingestion_logs
                    SET status = 'FAILED',
                        error_message = :err,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE ingestion_id = :ingestion_id;
                """),
                {"ingestion_id": ingestion_id, "err": str(exc)[:500]},
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
