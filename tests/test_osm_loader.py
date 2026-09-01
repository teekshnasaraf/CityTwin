from unittest.mock import MagicMock, call
import pytest
from shapely.geometry import Polygon

from backend.app.ingestion.osm.geocoder import ResolvedCity
from backend.app.ingestion.osm.validator import ValidationReport
from backend.app.ingestion.osm.loader import (
    get_or_create_osm_data_source,
    upsert_city,
    save_osm_city_data,
)


def test_get_or_create_osm_data_source_existing():
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.return_value = (42,)

    source_id = get_or_create_osm_data_source(mock_db)
    assert source_id == 42


def test_upsert_city_new():
    mock_db = MagicMock()
    # First select returns None (city doesn't exist)
    # Second insert returns city_id 1
    mock_db.execute.return_value.fetchone.side_effect = [None, (1,)]

    poly = Polygon([(80.20, 13.00), (80.30, 13.00), (80.30, 13.10), (80.20, 13.10), (80.20, 13.00)])
    city = ResolvedCity(
        name="Bengaluru",
        country="India",
        state="Karnataka",
        latitude=12.9716,
        longitude=77.5946,
        boundary=poly,
    )

    city_id = upsert_city(mock_db, city)
    assert city_id == 1


def test_save_osm_city_data_idempotent():
    mock_db = MagicMock()
    # 1. get_or_create_data_source -> (1,)
    # 2. upsert_city select -> (10,)
    # 3. insert ingestion_log -> (999,)
    mock_db.execute.return_value.fetchone.side_effect = [(1,), (10,), (999,)]

    poly = Polygon([(80.20, 13.00), (80.30, 13.00), (80.30, 13.10), (80.20, 13.10), (80.20, 13.00)])
    city = ResolvedCity(
        name="Chennai",
        country="India",
        state="Tamil Nadu",
        latitude=13.0827,
        longitude=80.2707,
        boundary=poly,
    )

    mock_roads = [{
        "city_id": 10,
        "osm_id": 101,
        "name": "Road A",
        "road_type": "primary",
        "length_m": 200.0,
        "speed_limit": 50.0,
        "lanes": 2,
        "capacity": None,
        "geometry_wkt": "LINESTRING(80.2 13.0, 80.3 13.0)",
    }]
    mock_intersections = [{
        "city_id": 10,
        "osm_id": 201,
        "geometry_wkt": "POINT(80.2 13.0)",
    }]
    mock_places = [{
        "city_id": 10,
        "osm_id": 301,
        "name": "Hospital X",
        "place_type": "hospital",
        "geometry_wkt": "POINT(80.25 13.05)",
    }]

    quality_reports = [
        ValidationReport(dataset_type="roads", total_records=1, valid_records=1, invalid_records=0, passed=True),
        ValidationReport(dataset_type="intersections", total_records=1, valid_records=1, invalid_records=0, passed=True),
        ValidationReport(dataset_type="places", total_records=1, valid_records=1, invalid_records=0, passed=True),
    ]

    result = save_osm_city_data(
        db=mock_db,
        city=city,
        roads=mock_roads,
        intersections=mock_intersections,
        places=mock_places,
        quality_reports=quality_reports,
    )

    assert result["status"] == "success"
    assert result["city"] == "Chennai"
    assert result["city_id"] == 10
    assert result["roads"] == 1
    assert result["intersections"] == 1
    assert result["places"] == 1
    assert result["ingestion_id"] == 999
    assert mock_db.commit.called
