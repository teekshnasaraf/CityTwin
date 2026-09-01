import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger("citytwin.ingestion.osm.transformer")


def parse_speed_limit(val: Any) -> Optional[float]:
    """
    Parses speed limit from OSM 'maxspeed' tags without inventing values.
    Returns float speed in km/h or None if unavailable/unparseable.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else None
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    
    val_str = str(val).strip().lower()
    match = re.search(r"(\d+(\.\d+)?)", val_str)
    if match:
        speed = float(match.group(1))
        if "mph" in val_str:
            speed = round(speed * 1.60934, 2)
        return speed
    return None


def parse_lanes(val: Any) -> Optional[int]:
    """
    Parses lane count from OSM 'lanes' tag.
    Returns int or None if unavailable.
    """
    if val is None:
        return None
    if isinstance(val, int):
        return val if val > 0 else None
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    
    match = re.search(r"^(\d+)", str(val).strip())
    if match:
        lanes = int(match.group(1))
        return lanes if lanes > 0 else None
    return None


def parse_string_tag(val: Any) -> Optional[str]:
    """
    Extracts a clean string from an OSM tag value (handles lists and nan).
    """
    if val is None:
        return None
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null"):
        return None
    return val_str


def parse_osm_id(val: Any) -> Optional[int]:
    """
    Extracts a numeric OSM identifier (handles int, string, lists).
    """
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def transform_road_network(
    graph: nx.MultiDiGraph, city_id: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Converts an OSMnx MultiDiGraph into normalized dictionaries for 'roads' and 'intersections' tables.
    Preserves EPSG:4326 WKT geometries for PostGIS storage.
    """
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(graph, nodes=True, edges=True)

    # 1. Transform Intersection Nodes
    intersections: List[Dict[str, Any]] = []
    for node_id, row in nodes_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            geom = Point(float(row["x"]), float(row["y"]))
        
        osm_id = parse_osm_id(node_id)
        intersections.append({
            "city_id": city_id,
            "osm_id": osm_id,
            "geometry": geom,
            "geometry_wkt": geom.wkt,
        })

    # 2. Transform Road Edges
    roads: List[Dict[str, Any]] = []
    for (u, v, k), row in edges_gdf.iterrows():
        geom = row.get("geometry")
        if geom is None or geom.is_empty:
            # Reconstruct straight LineString between node coordinates if edge geometry is missing
            u_node = nodes_gdf.loc[u]
            v_node = nodes_gdf.loc[v]
            geom = LineString([(u_node["x"], u_node["y"]), (v_node["x"], v_node["y"])])

        osm_id = parse_osm_id(row.get("osmid"))
        name = parse_string_tag(row.get("name"))
        road_type = parse_string_tag(row.get("highway"))
        
        # Length in meters
        length_val = row.get("length")
        length_m = float(length_val) if length_val is not None else float(geom.length)

        speed_limit = parse_speed_limit(row.get("maxspeed"))
        lanes = parse_lanes(row.get("lanes"))

        roads.append({
            "city_id": city_id,
            "osm_id": osm_id,
            "name": name,
            "road_type": road_type,
            "length_m": round(length_m, 2),
            "speed_limit": speed_limit,
            "lanes": lanes,
            "capacity": None,  # Explicitly NULL - never fabricated
            "geometry": geom,
            "geometry_wkt": geom.wkt,
        })

    logger.info("Transformed %d road segments and %d intersections for city_id=%d", len(roads), len(intersections), city_id)
    return roads, intersections


def transform_pois(features_gdf: gpd.GeoDataFrame, city_id: int) -> List[Dict[str, Any]]:
    """
    Transforms a GeoDataFrame of OSM POI features into normalized dictionaries for the 'places' table.
    Ensures geometry is a Point (centroid) because the 'places.geometry' column expects Point.
    """
    places: List[Dict[str, Any]] = []
    if features_gdf is None or features_gdf.empty:
        return places

    for element_id, row in features_gdf.iterrows():
        geom = row.get("geometry")
        if geom is None or geom.is_empty:
            continue

        # Ensure geometry is a Point; if not, use centroid
        if not isinstance(geom, Point):
            geom_point = geom.centroid
        else:
            geom_point = geom

        # Determine best place_type from tags
        place_type = (
            parse_string_tag(row.get("amenity"))
            or parse_string_tag(row.get("healthcare"))
            or parse_string_tag(row.get("emergency"))
            or parse_string_tag(row.get("public_transport"))
            or parse_string_tag(row.get("building"))
            or "poi"
        )

        name = parse_string_tag(row.get("name"))
        
        # OSM ID from index or attribute
        osm_id = None
        if isinstance(element_id, tuple) and len(element_id) >= 2:
            osm_id = parse_osm_id(element_id[1])
        else:
            osm_id = parse_osm_id(element_id)

        places.append({
            "city_id": city_id,
            "osm_id": osm_id,
            "name": name,
            "place_type": place_type,
            "geometry": geom_point,
            "geometry_wkt": geom_point.wkt,
        })

    logger.info("Transformed %d places/POIs for city_id=%d", len(places), city_id)
    return places
