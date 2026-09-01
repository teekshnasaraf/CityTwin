"""
Parser module for OSM data.
Re-exports transformation and parsing utilities from transformer.py for backwards compatibility.
"""
from .transformer import (
    parse_speed_limit,
    parse_lanes,
    parse_string_tag,
    parse_osm_id,
    transform_road_network,
    transform_pois,
)

__all__ = [
    "parse_speed_limit",
    "parse_lanes",
    "parse_string_tag",
    "parse_osm_id",
    "transform_road_network",
    "transform_pois",
]
