from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException

from backend.app.api.ingestion import ingest_city_from_osm, CityNotFoundError, OSMDownloadError
from backend.app.schemas.ingestion import CityIngestionRequest


def test_ingest_city_endpoint_success():
    payload = CityIngestionRequest(city="Chennai", country="India")
    mock_db = MagicMock()
    mock_result = {
        "status": "success",
        "city": "Chennai",
        "city_id": 1,
        "roads": 120,
        "intersections": 80,
        "places": 15,
        "ingestion_id": 1,
    }

    with patch("backend.app.api.ingestion.ingest_osm_city", return_value=mock_result):
        resp = ingest_city_from_osm(payload=payload, db=mock_db)
        assert resp.status == "success"
        assert resp.city == "Chennai"
        assert resp.city_id == 1
        assert resp.roads == 120
        assert resp.intersections == 80
        assert resp.places == 15
        assert resp.ingestion_id == 1


def test_ingest_city_endpoint_not_found():
    payload = CityIngestionRequest(city="FakeCity12345", country="Unknown")
    mock_db = MagicMock()

    with patch("backend.app.api.ingestion.ingest_osm_city", side_effect=CityNotFoundError("Not found")):
        with pytest.raises(HTTPException) as exc_info:
            ingest_city_from_osm(payload=payload, db=mock_db)
        assert exc_info.value.status_code == 404
        assert "could not be resolved" in exc_info.value.detail


def test_ingest_city_endpoint_osm_error():
    payload = CityIngestionRequest(city="Chennai", country="India")
    mock_db = MagicMock()

    with patch("backend.app.api.ingestion.ingest_osm_city", side_effect=OSMDownloadError("OSM 503")):
        with pytest.raises(HTTPException) as exc_info:
            ingest_city_from_osm(payload=payload, db=mock_db)
        assert exc_info.value.status_code == 502
        assert "Failed to retrieve data from OpenStreetMap" in exc_info.value.detail
