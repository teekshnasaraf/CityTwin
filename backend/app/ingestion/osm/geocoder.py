import logging
from dataclasses import dataclass
from typing import Optional
import osmnx as ox
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger("citytwin.ingestion.osm.geocoder")

# Configure OSMnx settings with project user-agent
ox.settings.user_agent = "CITYTWIN-Urban-Digital-Twin/1.0"
ox.settings.log_console = False
ox.settings.use_cache = True


class CityNotFoundError(Exception):
    """Raised when a city and country cannot be geocoded by OpenStreetMap/Nominatim."""
    pass


@dataclass
class ResolvedCity:
    name: str
    country: str
    state: Optional[str]
    latitude: float
    longitude: float
    boundary: BaseGeometry


def resolve_city(city: str, country: str) -> ResolvedCity:
    """
    Geocodes a city and country using OpenStreetMap / Nominatim via OSMnx.
    Returns the resolved boundary geometry (EPSG:4326), coordinates, and metadata.
    """
    clean_city = city.strip()
    clean_country = country.strip()
    query = f"{clean_city}, {clean_country}"
    
    logger.info("Resolving geographic boundary for: %s", query)
    
    try:
        gdf = ox.geocode_to_gdf(query)
    except Exception as exc:
        logger.warning("Geocoding failed for '%s': %s", query, str(exc))
        raise CityNotFoundError(f"Could not resolve city '{clean_city}, {clean_country}' via OpenStreetMap: {exc}") from exc

    if gdf is None or gdf.empty:
        raise CityNotFoundError(f"No geographic boundary found for '{clean_city}, {clean_country}'.")

    first_row = gdf.iloc[0]
    geometry = first_row.geometry

    if geometry is None or geometry.is_empty:
        raise CityNotFoundError(f"Resolved location for '{clean_city}, {clean_country}' has an empty boundary geometry.")

    # Coerce to MultiPolygon to match schema GEOMETRY(MultiPolygon, 4326)
    if isinstance(geometry, Polygon):
        geometry = MultiPolygon([geometry])

    # Calculate centroid coordinates if lat/lon not directly available in columns
    lat = float(first_row.get("lat", geometry.centroid.y))
    lon = float(first_row.get("lon", geometry.centroid.x))

    # Extract state/region if provided by Nominatim display_name
    display_name = str(first_row.get("display_name", ""))
    state = None
    if display_name:
        parts = [p.strip() for p in display_name.split(",")]
        if len(parts) >= 3:
            # Common Nominatim format: [City, County/District, State, Country]
            state = parts[-2]

    return ResolvedCity(
        name=clean_city,
        country=clean_country,
        state=state,
        latitude=lat,
        longitude=lon,
        boundary=geometry,
    )
