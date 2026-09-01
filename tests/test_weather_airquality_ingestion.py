"""
Unit tests for Weather, Air Quality, and Traffic Telemetry Ingestion Pipelines.
"""
from backend.app.ingestion.weather.client import WeatherAPIClient
from backend.app.ingestion.weather.loader import WeatherLoader
from backend.app.ingestion.air_quality.client import OpenAQClient
from backend.app.ingestion.air_quality.loader import AirQualityLoader
from backend.app.ingestion.traffic.client import TrafficFeedClient
from backend.app.ingestion.traffic.loader import TrafficLoader


class MockSession:
    def add(self, item): pass
    def commit(self): pass
    def rollback(self): pass
    def refresh(self, item):
        item.weather_id = 1


def test_weather_client_and_loader():
    """Verify Weather API client and quality validation loader."""
    obs = WeatherAPIClient.fetch_current_weather()
    assert "temperature" in obs
    assert "humidity" in obs
    assert obs["temperature"] > -50.0

    db = MockSession()
    res = WeatherLoader.load_weather_data(db=db, city_id=1)
    assert res["status"] == "COMPLETED"


def test_openaq_client_and_loader():
    """Verify OpenAQ air quality client and loader."""
    measurements = OpenAQClient.fetch_city_air_quality("Chennai")
    assert len(measurements) > 0
    assert "pollutant" in measurements[0]

    db = MockSession()
    res = AirQualityLoader.load_air_quality_data(db=db, city_id=1)
    assert res["status"] == "COMPLETED"


def test_traffic_telemetry_client_and_loader():
    """Verify Traffic Telemetry feed client and loader."""
    rows = TrafficFeedClient.fetch_latest_traffic_telemetry(city_id=1)
    assert len(rows) > 0
    assert "congestion_level" in rows[0]

    db = MockSession()
    res = TrafficLoader.load_traffic_telemetry(db=db, city_id=1)
    assert res["status"] == "COMPLETED"
