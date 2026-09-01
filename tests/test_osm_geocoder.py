from unittest.mock import patch, MagicMock
import pytest
import geopandas as gpd
from shapely.geometry import Polygon

from backend.app.ingestion.osm.geocoder import resolve_city, CityNotFoundError, ResolvedCity


def test_resolve_city_success():
    mock_poly = Polygon([(80.20, 13.00), (80.30, 13.00), (80.30, 13.10), (80.20, 13.10), (80.20, 13.00)])
    mock_gdf = gpd.GeoDataFrame(
        [{"lat": 13.0827, "lon": 80.2707, "display_name": "Chennai, Tamil Nadu, India"}],
        geometry=[mock_poly],
        crs="EPSG:4326",
    )

    with patch("osmnx.geocode_to_gdf", return_value=mock_gdf):
        result = resolve_city("Chennai", "India")
        assert isinstance(result, ResolvedCity)
        assert result.name == "Chennai"
        assert result.country == "India"
        assert result.latitude == 13.0827
        assert result.longitude == 80.2707
        assert result.boundary.equals(mock_poly)


def test_resolve_city_not_found():
    with patch("osmnx.geocode_to_gdf", side_effect=Exception("No match found")):
        with pytest.raises(CityNotFoundError):
            resolve_city("NonExistentCity12345", "UnknownCountry")


def test_resolve_city_empty_gdf():
    with patch("osmnx.geocode_to_gdf", return_value=gpd.GeoDataFrame()):
        with pytest.raises(CityNotFoundError):
            resolve_city("EmptyCity", "Country")
