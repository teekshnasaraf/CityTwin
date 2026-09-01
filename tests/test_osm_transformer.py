import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point, Polygon

from backend.app.ingestion.osm.transformer import (
    parse_speed_limit,
    parse_lanes,
    parse_string_tag,
    parse_osm_id,
    transform_road_network,
    transform_pois,
)


def test_parse_speed_limit():
    assert parse_speed_limit("50") == 50.0
    assert parse_speed_limit("60 km/h") == 60.0
    assert parse_speed_limit("30 mph") == 48.28
    assert parse_speed_limit(["40", "50"]) == 40.0
    assert parse_speed_limit(None) is None
    assert parse_speed_limit("signals") is None
    assert parse_speed_limit("walk") is None


def test_parse_lanes():
    assert parse_lanes("2") == 2
    assert parse_lanes("4") == 4
    assert parse_lanes(["3", "2"]) == 3
    assert parse_lanes(None) is None
    assert parse_lanes("unknown") is None


def test_parse_string_tag():
    assert parse_string_tag("Anna Salai") == "Anna Salai"
    assert parse_string_tag(["Main Road", "Alt Road"]) == "Main Road"
    assert parse_string_tag(None) is None
    assert parse_string_tag("nan") is None
    assert parse_string_tag("") is None


def test_parse_osm_id():
    assert parse_osm_id(12345) == 12345
    assert parse_osm_id("67890") == 67890
    assert parse_osm_id([111, 222]) == 111
    assert parse_osm_id(None) is None
    assert parse_osm_id("abc") is None


def test_transform_road_network():
    # Build a simple MultiDiGraph with 2 nodes and 1 edge
    G = nx.MultiDiGraph(crs="EPSG:4326")
    G.add_node(101, x=80.25, y=13.05, osmid=101)
    G.add_node(102, x=80.26, y=13.06, osmid=102)
    G.add_edge(
        101, 102, 0,
        osmid=999,
        name="Test Highway",
        highway="primary",
        length=150.5,
        maxspeed="60",
        lanes="3",
        geometry=LineString([(80.25, 13.05), (80.26, 13.06)]),
    )

    roads, intersections = transform_road_network(G, city_id=1)

    assert len(intersections) == 2
    assert intersections[0]["city_id"] == 1
    assert intersections[0]["geometry_wkt"].startswith("POINT")

    assert len(roads) == 1
    assert roads[0]["city_id"] == 1
    assert roads[0]["osm_id"] == 999
    assert roads[0]["name"] == "Test Highway"
    assert roads[0]["road_type"] == "primary"
    assert roads[0]["length_m"] == 150.5
    assert roads[0]["speed_limit"] == 60.0
    assert roads[0]["lanes"] == 3
    assert roads[0]["capacity"] is None
    assert roads[0]["geometry_wkt"].startswith("LINESTRING")


def test_transform_pois():
    mock_point = Point(80.25, 13.05)
    mock_gdf = gpd.GeoDataFrame(
        [
            {
                "amenity": "hospital",
                "name": "City General Hospital",
            }
        ],
        geometry=[mock_point],
        index=[123456],
        crs="EPSG:4326",
    )

    places = transform_pois(mock_gdf, city_id=1)
    assert len(places) == 1
    assert places[0]["city_id"] == 1
    assert places[0]["osm_id"] == 123456
    assert places[0]["name"] == "City General Hospital"
    assert places[0]["place_type"] == "hospital"
    assert places[0]["geometry_wkt"].startswith("POINT")
