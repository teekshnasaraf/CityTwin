import logging
import time
from typing import Any, Callable, Dict, Optional
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry.base import BaseGeometry

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings

logger = logging.getLogger("citytwin.ingestion.osm.downloader")

# Category tags for CityTwin urban points of interest
DEFAULT_POI_TAGS: Dict[str, Any] = {
    "amenity": [
        "hospital",
        "clinic",
        "doctors",
        "pharmacy",
        "school",
        "university",
        "college",
        "kindergarten",
        "police",
        "fire_station",
        "bus_station",
        "ferry_terminal",
        "townhall",
    ],
    "healthcare": ["hospital", "clinic"],
    "emergency": ["ambulance_station", "fire_station", "police"],
    "public_transport": ["station", "stop_position"],
}


class OSMDownloadError(Exception):
    """Raised when downloading OpenStreetMap network or POI data fails."""
    pass


def _execute_with_overpass_fallbacks(download_func: Callable) -> Any:
    """
    Executes an OSMnx download function, rotating through configured fallback
    endpoints if a network/SSL/timeout error occurs.
    """
    endpoints = [settings.OVERPASS_URL]
    if settings.OVERPASS_FALLBACK_URLS:
        endpoints.extend([u.strip() for u in settings.OVERPASS_FALLBACK_URLS.split(",") if u.strip()])

    ox.settings.requests_timeout = settings.OVERPASS_REQUEST_TIMEOUT
    ox.settings.use_cache = True  # Preserve caching globally

    last_exc = None
    for i, endpoint in enumerate(endpoints):
        ox.settings.overpass_url = endpoint
        logger.info("Attempting OSM download using endpoint: %s", endpoint)
        try:
            return download_func()
        except ox._errors.InsufficientResponseError as exc:
            # Re-raise insufficient response errors immediately (not a connection issue)
            raise exc
        except Exception as exc:
            logger.warning("Download failed on endpoint %s: %s", endpoint, str(exc))
            last_exc = exc
            if i < len(endpoints) - 1:
                logger.info("Waiting 5 seconds before falling back to next endpoint...")
                time.sleep(5)
            
    logger.error("All configured Overpass endpoints failed.")
    raise OSMDownloadError(f"All {len(endpoints)} Overpass endpoints failed. Last error: {last_exc}") from last_exc


def download_road_network(boundary: BaseGeometry, network_type: str = "drive") -> nx.MultiDiGraph:
    """
    Downloads the drivable road network graph for a given geographic boundary using OSMnx.
    Pure retrieval function - performs no database operations.
    """
    logger.info("Downloading '%s' road network for boundary...", network_type)
    
    def _do_download():
        return ox.graph_from_polygon(
            boundary,
            network_type=network_type,
            simplify=True,
            retain_all=False,
            truncate_by_edge=True,
        )
        
    try:
        graph = _execute_with_overpass_fallbacks(_do_download)
    except Exception as exc:
        logger.error("Failed to download road network: %s", str(exc))
        raise OSMDownloadError(f"OpenStreetMap road network download failed: {exc}") from exc

    if graph is None or len(graph.nodes) == 0:
        raise OSMDownloadError("Downloaded road network graph contains no nodes.")

    logger.info("Road network downloaded successfully: %d nodes, %d edges", len(graph.nodes), len(graph.edges))
    return graph


def download_pois(boundary: BaseGeometry, tags: Optional[Dict[str, Any]] = None) -> gpd.GeoDataFrame:
    """
    Downloads points of interest (POIs) and critical facilities for a given boundary.
    Pure retrieval function - performs no database operations.
    """
    query_tags = tags or DEFAULT_POI_TAGS
    logger.info("Downloading POI features with tags: %s", list(query_tags.keys()))
    
    def _do_download():
        return ox.features_from_polygon(boundary, tags=query_tags)
        
    try:
        features_gdf = _execute_with_overpass_fallbacks(_do_download)
    except ox._errors.InsufficientResponseError:
        logger.warning("No POI features found in the specified boundary.")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    except Exception as exc:
        logger.warning("POI download encountered an issue or found no elements: %s", str(exc))
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    if features_gdf is None or features_gdf.empty:
        logger.info("Downloaded 0 POI features.")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    logger.info("Downloaded %d POI features.", len(features_gdf))
    return features_gdf
