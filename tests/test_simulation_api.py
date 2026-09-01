"""
Integration API tests for Simulation endpoints.
"""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_simulation_run_endpoint():
    """Verify POST /api/v1/simulations/run endpoint."""
    response = client.post(
        "/api/v1/simulations/run",
        json={
            "city_id": 1,
            "closed_road_id": 101,
            "duration_hours": 4.0,
            "capacity_factor": 0.0,
            "traffic_factor": 1.0,
            "weather_factor": 1.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "traffic" in data
    assert "transit" in data
    assert "emergency" in data
    assert "pollution" in data
    assert "metrics" in data
    assert len(data["metrics"]) == 4


def test_simulation_recommendations_endpoint():
    """Verify GET /api/v1/simulations/recommendation/evaluate endpoint."""
    response = client.get(
        "/api/v1/simulations/recommendation/evaluate?city_id=1&closed_road_id=101&duration_hours=4.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert "best_option" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) == 3


def test_cities_and_state_endpoints():
    """Verify /cities and /cities/{id}/traffic/latest endpoints."""
    res_cities = client.get("/api/v1/cities")
    assert res_cities.status_code == 200

    res_traffic = client.get("/api/v1/cities/1/traffic/latest")
    assert res_traffic.status_code == 200
    data = res_traffic.json()
    assert "freshness_label" in data
    assert "data_type" in data
