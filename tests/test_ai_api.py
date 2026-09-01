"""
Integration API tests for Groq LLM AI REST Endpoints.
"""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_predict_traffic_endpoint():
    """Verify POST /api/v1/ai/predict-traffic Groq LLM prediction endpoint."""
    response = client.post(
        "/api/v1/ai/predict-traffic",
        json={
            "road_id": 101,
            "hour": 9,
            "day_of_week": 1,
            "temperature": 30.0,
            "rainfall": 0.0,
            "model_type": "llama-3.3-70b-versatile",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "predicted_vehicle_count" in data
    assert data["prediction_horizon_min"] == 15
    assert data["provenance"] == "PREDICTED_GROQ_LLM"
    assert "model_performance" in data


def test_train_and_compare_endpoint():
    """Verify POST /api/v1/ai/train Groq LLM candidate model evaluation endpoint."""
    response = client.post("/api/v1/ai/train?num_days=3")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert "best_model" in data
    assert "leaderboard" in data
