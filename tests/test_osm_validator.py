from shapely.geometry import LineString, Point, Polygon

from backend.app.ingestion.osm.validator import (
    validate_geometry,
    validate_roads,
    validate_intersections,
    validate_places,
)


def test_validate_geometry():
    assert validate_geometry(Point(0, 0))[0] is True
    assert validate_geometry(LineString([(0, 0), (1, 1)]))[0] is True
    assert validate_geometry(None)[0] is False
    assert validate_geometry("invalid_type")[0] is False
    assert validate_geometry(Point())[0] is False  # empty point


def test_validate_roads_filtering():
    valid_road = {
        "city_id": 1,
        "osm_id": 101,
        "name": "Valid Road",
        "road_type": "primary",
        "length_m": 120.0,
        "speed_limit": 50.0,
        "lanes": 2,
        "geometry": LineString([(80.0, 13.0), (80.1, 13.1)]),
    }
    invalid_road_null_geom = {
        "city_id": 1,
        "osm_id": 102,
        "name": "Invalid Road",
        "road_type": "primary",
        "length_m": 120.0,
        "geometry": None,
    }
    invalid_road_negative_length = {
        "city_id": 1,
        "osm_id": 103,
        "name": "Negative Length Road",
        "road_type": "primary",
        "length_m": -5.0,
        "geometry": LineString([(80.0, 13.0), (80.1, 13.1)]),
    }

    records = [valid_road, invalid_road_null_geom, invalid_road_negative_length]
    valid, report = validate_roads(records)

    assert len(valid) == 1
    assert valid[0]["osm_id"] == 101
    assert report.total_records == 3
    assert report.valid_records == 1
    assert report.invalid_records == 2
    assert report.passed is True
    assert "geometry_is_null" in report.rejection_reasons


def test_validate_intersections():
    valid_int = {
        "city_id": 1,
        "osm_id": 501,
        "geometry": Point(80.25, 13.05),
    }
    invalid_int = {
        "city_id": 1,
        "osm_id": 502,
        "geometry": None,
    }

    valid, report = validate_intersections([valid_int, invalid_int])
    assert len(valid) == 1
    assert report.total_records == 2
    assert report.valid_records == 1
    assert report.invalid_records == 1


def test_validate_places():
    valid_place = {
        "city_id": 1,
        "osm_id": 901,
        "name": "General Hospital",
        "place_type": "hospital",
        "geometry": Point(80.25, 13.05),
    }
    invalid_place = {
        "city_id": 1,
        "osm_id": 902,
        "name": "Mystery Place",
        "place_type": None,
        "geometry": Point(80.25, 13.05),
    }

    valid, report = validate_places([valid_place, invalid_place])
    assert len(valid) == 1
    assert valid[0]["place_type"] == "hospital"
    assert report.total_records == 2
    assert report.valid_records == 1
