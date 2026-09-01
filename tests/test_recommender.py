"""
Unit tests for Multi-Objective Intervention Recommender Engine.
"""
from backend.app.optimization.recommender import InterventionRecommender


class DummySession:
    """Mock DB session for testing recommender without active DB."""
    def query(self, *args, **kwargs):
        return self
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        return None
    def all(self):
        return []
    def execute(self, *args, **kwargs):
        class MockResult:
            def fetchall(self):
                return []
        return MockResult()


def test_evaluate_interventions():
    """Verify multi-candidate evaluation, scoring, and ranking output."""
    db = DummySession()

    result = InterventionRecommender.evaluate_interventions(
        db=db,
        city_id=1,
        closed_road_id=101,
        duration_hours=4.0,
        weights={"emergency": 0.40, "traffic": 0.30, "transit": 0.15, "pollution": 0.15},
    )

    assert "best_option" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) == 3

    # Check rank ordering (rank 1 should have lowest composite impact score)
    ranks = [r["rank"] for r in result["recommendations"]]
    scores = [r["score"] for r in result["recommendations"]]

    assert ranks == [1, 2, 3]
    assert scores[0] <= scores[1] <= scores[2]
