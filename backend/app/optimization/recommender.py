"""
Multi-Objective Optimization & Intervention Recommendation Engine.
Evaluates alternative candidate strategies (Full Closure, Partial Closure, Night Closure),
computes weighted composite impact scores, and recommends the lowest-impact intervention.
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.simulation.engine import DigitalTwinEngine

logger = logging.getLogger("citytwin.optimization.recommender")


class InterventionRecommender:
    """Evaluates multi-domain interventions and ranks recommendations."""

    # Default configurable priority weights
    DEFAULT_WEIGHTS = {
        "emergency": 0.40,
        "traffic": 0.30,
        "transit": 0.15,
        "pollution": 0.15,
    }

    @classmethod
    def evaluate_interventions(
        cls,
        db: Session,
        city_id: int,
        closed_road_id: int,
        duration_hours: float = 4.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates candidate interventions (Option A, Option B, Option C),
        scores each option against weighted criteria, and ranks recommendations.
        """
        effective_weights = cls.DEFAULT_WEIGHTS.copy()
        if weights:
            effective_weights.update(weights)

        # Normalize weights to sum to 1.0
        total_w = sum(effective_weights.values())
        if total_w > 0:
            effective_weights = {k: v / total_w for k, v in effective_weights.items()}

        candidates = [
            {
                "name": "Option A — Full Closure",
                "capacity_factor": 0.0,
                "traffic_factor": 1.0,
                "weather_factor": 1.0,
                "description": "Complete closure of the selected road segment for full duration.",
            },
            {
                "name": "Option B — Partial Lane Closure",
                "capacity_factor": 0.5,
                "traffic_factor": 1.0,
                "weather_factor": 1.0,
                "description": "Close 50% of lanes to maintain partial traffic flow during work.",
            },
            {
                "name": "Option C — Night / Off-Peak Closure",
                "capacity_factor": 0.8,
                "traffic_factor": 0.6,
                "weather_factor": 1.0,
                "description": "Shift work to off-peak night hours with reduced traffic volume.",
            },
        ]

        scored_options = []
        for cand in candidates:
            sim_res = DigitalTwinEngine.run_scenario_simulation(
                db=db,
                city_id=city_id,
                closed_road_id=closed_road_id,
                duration_hours=duration_hours,
                capacity_factor=cand["capacity_factor"],
                traffic_factor=cand["traffic_factor"],
                weather_factor=cand["weather_factor"],
            )

            # Extract metric percentage changes (non-negative impact penalties)
            traffic_penalty = max(0.0, sim_res["traffic"]["change_percent"])
            transit_penalty = max(0.0, sim_res["transit"]["change_percent"])
            emergency_penalty = max(0.0, sim_res["emergency"]["change_percent"])
            pollution_penalty = max(0.0, sim_res["pollution"]["change_percent"])

            # Compute weighted composite impact score (lower is better)
            composite_score = (
                effective_weights["emergency"] * (emergency_penalty / 100.0)
                + effective_weights["traffic"] * (traffic_penalty / 100.0)
                + effective_weights["transit"] * (transit_penalty / 100.0)
                + effective_weights["pollution"] * (pollution_penalty / 100.0)
            )

            scored_options.append(
                {
                    "intervention": cand["name"],
                    "capacity_factor": cand["capacity_factor"],
                    "score": round(composite_score, 4),
                    "penalties": {
                        "emergency_pct": emergency_penalty,
                        "traffic_pct": traffic_penalty,
                        "transit_pct": transit_penalty,
                        "pollution_pct": pollution_penalty,
                    },
                    "simulation": sim_res,
                }
            )

        # Rank candidates by composite score ascending (lowest impact = rank 1)
        scored_options.sort(key=lambda x: x["score"])

        recommendations = []
        for rank, opt in enumerate(scored_options, start=1):
            if rank == 1:
                reason = (
                    f"Recommended choice: {opt['intervention']} minimizes composite cascading impact "
                    f"(Score: {opt['score']}) by maintaining emergency response time stability "
                    f"and reducing bus network delays."
                )
            else:
                reason = (
                    f"Alternative choice ({opt['intervention']}) results in higher composite impact score "
                    f"({opt['score']}) due to increased network congestion and emergency ETA delays."
                )

            recommendations.append(
                {
                    "rank": rank,
                    "intervention": opt["intervention"],
                    "score": opt["score"],
                    "reason": reason,
                    "simulation": opt["simulation"],
                }
            )

        return {
            "city_id": city_id,
            "closed_road_id": closed_road_id,
            "weights": effective_weights,
            "best_option": recommendations[0]["intervention"],
            "best_score": recommendations[0]["score"],
            "recommendations": recommendations,
        }
