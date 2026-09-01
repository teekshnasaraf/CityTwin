"""
Pollution & Environmental Impact Estimation Model.
Computes traffic emission and air quality shifts based on vehicle activity,
congestion levels, and weather multipliers.
"""
import logging
import networkx as nx
from typing import Dict, Any

logger = logging.getLogger("citytwin.simulation.pollution")


class PollutionEstimator:
    """Estimates pollution impact metrics using transparent activity-congestion formulas."""

    @classmethod
    def estimate_pollution_impact(
        cls, baseline_graph: nx.DiGraph, scenario_graph: nx.DiGraph, weather_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Computes baseline vs scenario emission scores and returns percentage shifts.
        Formula per edge: length_m * vehicle_count * (1 + 0.5 * congestion) * weather_factor
        """
        baseline_index = cls._calculate_emission_index(baseline_graph, weather_factor=1.0)
        scenario_index = cls._calculate_emission_index(scenario_graph, weather_factor=weather_factor)

        pct_change = ((scenario_index - baseline_index) / max(1.0, baseline_index)) * 100.0

        return {
            "baseline_pollution_index": round(baseline_index, 2),
            "scenario_pollution_index": round(scenario_index, 2),
            "change_percent": round(pct_change, 2),
        }

    @staticmethod
    def _calculate_emission_index(G: nx.DiGraph, weather_factor: float) -> float:
        """Sums activity-weighted emission score across all edges."""
        total_emission = 0.0
        for u, v, d in G.edges(data=True):
            length = d.get("length_m", 500.0) / 1000.0  # km
            v_count = d.get("vehicle_count", 200)
            congestion = d.get("congestion_level", 0.1)
            # Emission increases with idling and heavy stop-and-go congestion
            edge_emission = length * v_count * (1.0 + 0.6 * congestion) * weather_factor
            total_emission += edge_emission
        return total_emission / 100.0  # Scaled index
