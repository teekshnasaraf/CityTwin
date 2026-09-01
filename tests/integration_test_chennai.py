"""
Integration test: OSM ingestion for Chennai, India.
Uses the application's own database configuration and ingestion pipeline.
This is a one-time test script — NOT production code.
"""
import sys
import os
import logging

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("integration_test")

def test_db_connection():
    """Test that the app's DB engine can connect."""
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar()
            logger.info("Database connected: %s", version[:80])
            postgis = conn.execute(text("SELECT PostGIS_Version();")).scalar()
            logger.info("PostGIS version: %s", postgis)
        return True
    except Exception as exc:
        logger.error("DB Connection FAILED: %s", str(exc))
        return False

def run_ingestion():
    """Run the full OSM ingestion pipeline for Chennai, India via the API endpoint."""
    from app.main import app
    from fastapi.testclient import TestClient

    logger.info("=" * 60)
    logger.info("Starting OSM ingestion via API: POST /api/v1/ingestion/osm/city")
    logger.info("=" * 60)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/ingestion/osm/city",
            json={"city": "Chennai", "country": "India"}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("=" * 60)
            logger.info("Ingestion result: %s", result)
            logger.info("=" * 60)
            return result
        else:
            logger.error("Ingestion FAILED with status %d: %s", response.status_code, response.text)
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as exc:
        logger.error("Ingestion Exception: %s", str(exc))
        return {"error": str(exc)}

def verify_database(city_id: int):
    """Query PostgreSQL to verify all ingested data."""
    from app.database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            logger.info("=" * 60)
            logger.info("DATABASE VERIFICATION")
            logger.info("=" * 60)

            # 1. City record
            city_row = conn.execute(
                text("SELECT city_id, name, country, state, latitude, longitude, ST_GeometryType(boundary), ST_SRID(boundary) FROM cities WHERE city_id = :cid;"),
                {"cid": city_id}
            ).fetchone()
            if city_row:
                logger.info("CITY: id=%s, name='%s', country='%s', state='%s', lat=%s, lon=%s, geom_type=%s, srid=%s",
                            *city_row)
            else:
                logger.error("NO CITY FOUND with city_id=%d", city_id)

            # 2. Total city count
            total_cities = conn.execute(text("SELECT COUNT(*) FROM cities;")).scalar()
            logger.info("Total cities in DB: %d", total_cities)

            # 3. Roads
            road_count = conn.execute(text("SELECT COUNT(*) FROM roads WHERE city_id = :cid;"), {"cid": city_id}).scalar()
            road_zero = conn.execute(text("SELECT COUNT(*) FROM roads WHERE city_id = 0;")).scalar()
            road_orphan = conn.execute(text("SELECT COUNT(*) FROM roads WHERE city_id NOT IN (SELECT city_id FROM cities);")).scalar()
            road_srid = conn.execute(text("SELECT DISTINCT ST_SRID(geometry) FROM roads WHERE city_id = :cid LIMIT 5;"), {"cid": city_id}).fetchall()
            logger.info("ROADS: count=%d, city_id=0 count=%d, orphaned=%d, SRIDs=%s", road_count, road_zero, road_orphan, [r[0] for r in road_srid])

            # 4. Intersections
            int_count = conn.execute(text("SELECT COUNT(*) FROM intersections WHERE city_id = :cid;"), {"cid": city_id}).scalar()
            int_zero = conn.execute(text("SELECT COUNT(*) FROM intersections WHERE city_id = 0;")).scalar()
            int_orphan = conn.execute(text("SELECT COUNT(*) FROM intersections WHERE city_id NOT IN (SELECT city_id FROM cities);")).scalar()
            int_srid = conn.execute(text("SELECT DISTINCT ST_SRID(geometry) FROM intersections WHERE city_id = :cid LIMIT 5;"), {"cid": city_id}).fetchall()
            logger.info("INTERSECTIONS: count=%d, city_id=0 count=%d, orphaned=%d, SRIDs=%s", int_count, int_zero, int_orphan, [r[0] for r in int_srid])

            # 5. Places
            place_count = conn.execute(text("SELECT COUNT(*) FROM places WHERE city_id = :cid;"), {"cid": city_id}).scalar()
            place_zero = conn.execute(text("SELECT COUNT(*) FROM places WHERE city_id = 0;")).scalar()
            place_orphan = conn.execute(text("SELECT COUNT(*) FROM places WHERE city_id NOT IN (SELECT city_id FROM cities);")).scalar()
            place_srid = conn.execute(text("SELECT DISTINCT ST_SRID(geometry) FROM places WHERE city_id = :cid LIMIT 5;"), {"cid": city_id}).fetchall()
            logger.info("PLACES: count=%d, city_id=0 count=%d, orphaned=%d, SRIDs=%s", place_count, place_zero, place_orphan, [r[0] for r in place_srid])

            # 6. Ingestion logs
            log_rows = conn.execute(
                text("SELECT ingestion_id, source_id, dataset_type, status, records_received, records_inserted, records_updated, records_failed, error_message FROM ingestion_logs ORDER BY ingestion_id DESC LIMIT 3;")
            ).fetchall()
            for row in log_rows:
                logger.info("INGESTION_LOG: ingestion_id=%s, source_id=%s, type=%s, status=%s, received=%s, inserted=%s, updated=%s, failed=%s, error=%s",
                            *row)

            # 7. Data quality logs
            if log_rows:
                latest_ingestion_id = log_rows[0][0]
                quality_rows = conn.execute(
                    text("SELECT table_name, records_checked, records_valid, records_invalid, quality_score FROM data_quality_logs WHERE ingestion_id = :iid;"),
                    {"iid": latest_ingestion_id}
                ).fetchall()
                for qr in quality_rows:
                    logger.info("DATA_QUALITY: table=%s, checked=%s, valid=%s, invalid=%s, score=%s", *qr)

            # 8. Data sources
            ds_row = conn.execute(
                text("SELECT source_id, name, source_type, base_url FROM data_sources WHERE name = 'OpenStreetMap';")
            ).fetchone()
            if ds_row:
                logger.info("DATA_SOURCE: id=%s, name='%s', type='%s', base_url='%s'", *ds_row)

            # 9. Sample road geometry types
            road_types = conn.execute(
                text("SELECT DISTINCT ST_GeometryType(geometry) FROM roads WHERE city_id = :cid LIMIT 5;"),
                {"cid": city_id}
            ).fetchall()
            logger.info("Road geometry types: %s", [r[0] for r in road_types])

            # 10. Sample intersection geometry types
            int_types = conn.execute(
                text("SELECT DISTINCT ST_GeometryType(geometry) FROM intersections WHERE city_id = :cid LIMIT 5;"),
                {"cid": city_id}
            ).fetchall()
            logger.info("Intersection geometry types: %s", [r[0] for r in int_types])

            return {
                "city": city_row,
                "total_cities": total_cities,
                "roads": road_count,
                "intersections": int_count,
                "places": place_count,
                "roads_city0": road_zero,
                "intersections_city0": int_zero,
                "places_city0": place_zero,
                "roads_orphan": road_orphan,
                "intersections_orphan": int_orphan,
                "places_orphan": place_orphan,
            }
    except Exception as exc:
        logger.error("DB Verification FAILED: %s", str(exc))
        return {"error": str(exc)}


if __name__ == "__main__":
    logger.info("Phase 1: Testing database connection...")
    test_db_connection()

    logger.info("Phase 2: Running OSM ingestion pipeline...")
    result = run_ingestion()

    logger.info("Phase 3: Verifying database state...")
    city_id = result.get("city_id", -1) if isinstance(result, dict) else -1
    db_state = verify_database(city_id)

    logger.info("=" * 60)
    logger.info("INTEGRATION TEST COMPLETE")
    logger.info("=" * 60)
