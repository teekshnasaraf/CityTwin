import pytest
from unittest.mock import patch, MagicMock
from shapely.geometry import Polygon
import osmnx as ox

from backend.app.ingestion.osm.downloader import download_road_network, OSMDownloadError


@pytest.fixture
def mock_boundary():
    return Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr("backend.app.ingestion.osm.downloader.settings.OVERPASS_URL", "http://primary")
    monkeypatch.setattr("backend.app.ingestion.osm.downloader.settings.OVERPASS_FALLBACK_URLS", "http://fallback1, http://fallback2")
    monkeypatch.setattr("backend.app.ingestion.osm.downloader.settings.OVERPASS_REQUEST_TIMEOUT", 10)


@patch("backend.app.ingestion.osm.downloader.ox.graph_from_polygon")
@patch("backend.app.ingestion.osm.downloader.time.sleep")
def test_download_road_network_success_primary(mock_sleep, mock_graph, mock_boundary, mock_settings):
    # Mock successful graph download
    mock_graph.return_value = MagicMock(nodes=[1, 2], edges=[(1, 2)])
    
    graph = download_road_network(mock_boundary)
    
    assert graph is not None
    assert mock_graph.call_count == 1
    assert ox.settings.overpass_url == "http://primary"
    assert ox.settings.use_cache is True
    assert ox.settings.requests_timeout == 10
    mock_sleep.assert_not_called()


@patch("backend.app.ingestion.osm.downloader.ox.graph_from_polygon")
@patch("backend.app.ingestion.osm.downloader.time.sleep")
def test_download_road_network_fallback_success(mock_sleep, mock_graph, mock_boundary, mock_settings):
    # First call fails, second call succeeds
    mock_graph.side_effect = [
        Exception("Connection Error"),
        MagicMock(nodes=[1, 2], edges=[(1, 2)])
    ]
    
    graph = download_road_network(mock_boundary)
    
    assert graph is not None
    assert mock_graph.call_count == 2
    assert ox.settings.overpass_url == "http://fallback1"
    mock_sleep.assert_called_once_with(5)


@patch("backend.app.ingestion.osm.downloader.ox.graph_from_polygon")
@patch("backend.app.ingestion.osm.downloader.time.sleep")
def test_download_road_network_all_fail(mock_sleep, mock_graph, mock_boundary, mock_settings):
    # All three configured endpoints fail
    mock_graph.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        Exception("Error 3")
    ]
    
    with pytest.raises(OSMDownloadError) as exc_info:
        download_road_network(mock_boundary)
        
    assert "All 3 Overpass endpoints failed" in str(exc_info.value)
    assert mock_graph.call_count == 3
    assert ox.settings.overpass_url == "http://fallback2"
    assert mock_sleep.call_count == 2


@patch("backend.app.ingestion.osm.downloader.ox.graph_from_polygon")
@patch("backend.app.ingestion.osm.downloader.time.sleep")
def test_download_road_network_insufficient_response(mock_sleep, mock_graph, mock_boundary, mock_settings):
    # Insufficient response should NOT trigger fallback
    mock_graph.side_effect = ox._errors.InsufficientResponseError("No nodes")
    
    with pytest.raises(OSMDownloadError):
        download_road_network(mock_boundary)
        
    assert mock_graph.call_count == 1
    mock_sleep.assert_not_called()
