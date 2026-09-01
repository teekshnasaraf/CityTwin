from .geocoder import resolve_city, ResolvedCity, CityNotFoundError
from .downloader import download_road_network, download_pois, OSMDownloadError
from .transformer import transform_road_network, transform_pois
from .validator import (
    validate_roads,
    validate_intersections,
    validate_places,
    ValidationReport,
)
from .loader import save_osm_city_data
import logging
from typing import Any, Dict
from sqlalchemy.orm import Session

logger = logging.getLogger("citytwin.ingestion.osm")


def ingest_osm_city(city: str, country: str, db: Session) -> Dict[str, Any]:
    """
    End-to-end orchestration pipeline for OpenStreetMap city ingestion:
    1. Geocode boundary
    2. Download drivable road network and POIs
    3. Transform to PostGIS schema structures
    4. Validate geometries and attributes
    5. Transactionally load into PostgreSQL/PostGIS with data provenance
    """
    logger.info("Starting OSM ingestion for %s, %s", city, country)

    # 1. Geocode City
    resolved_city = resolve_city(city, country)

    # 2. Download Raw Datasets
    road_graph = download_road_network(resolved_city.boundary)
    pois_gdf = download_pois(resolved_city.boundary)

    # 3. Transform to Schema Formats
    # Use temporary city_id 0 during transformation, real city_id is assigned in loader
    raw_roads, raw_intersections = transform_road_network(road_graph, city_id=0)
    raw_places = transform_pois(pois_gdf, city_id=0)

    # 4. Validate Datasets
    valid_roads, roads_report = validate_roads(raw_roads)
    valid_intersections, intersections_report = validate_intersections(raw_intersections)
    valid_places, places_report = validate_places(raw_places)

    quality_reports = [roads_report, intersections_report, places_report]

    # 5. Transactional Database Load
    result = save_osm_city_data(
        db=db,
        city=resolved_city,
        roads=valid_roads,
        intersections=valid_intersections,
        places=valid_places,
        quality_reports=quality_reports,
    )

    logger.info("Completed OSM ingestion pipeline for %s (city_id=%d)", city, result["city_id"])
    return result


__all__ = [
    "ingest_osm_city",
    "resolve_city",
    "ResolvedCity",
    "CityNotFoundError",
    "download_road_network",
    "download_pois",
    "OSMDownloadError",
    "transform_road_network",
    "transform_pois",
    "validate_roads",
    "validate_intersections",
    "validate_places",
    "ValidationReport",
    "save_osm_city_data",
]
