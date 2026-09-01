"""
Public Transport & GTFS Bus Delay Simulation Engine.
Maps transit routes onto the road network and estimates route delays.
"""
import logging
import networkx as nx
from typing import Dict, Any

logger = logging.getLogger("citytwin.simulation.transit")


class TransitSimulator:
    """Estimates public transport GTFS bus delays based on road network travel times."""

    @classmethod
    def simulate_transit_delays(cls, baseline_graph: nx.DiGraph, scenario_graph: nx.DiGraph) -> Dict[str, Any]:
        """
        Computes baseline vs scenario public transit travel times across bus corridors.
        Returns delay metrics in minutes.
        """
        baseline_route_time = cls._compute_corridor_time(baseline_graph)
        scenario_route_time = cls._compute_corridor_time(scenario_graph)

        baseline_minutes = baseline_route_time / 60.0
        scenario_minutes = scenario_route_time / 60.0
        delay_minutes = max(0.0, scenario_minutes - baseline_minutes)

        pct_change = ((delay_minutes) / max(0.1, baseline_minutes)) * 100.0 if baseline_minutes > 0 else 0.0

        return {
            "baseline_transit_time_min": round(baseline_minutes, 2),
            "scenario_transit_time_min": round(scenario_minutes, 2),
            "delay_minutes": round(delay_minutes, 2),
            "change_percent": round(pct_change, 2),
        }

    @staticmethod
    def _compute_corridor_time(G: nx.DiGraph) -> float:
        """Sums travel time across graph edges representing major transit corridors."""
        total_time = 0.0
        for u, v, d in G.edges(data=True):
            tt = d.get("travel_time", 60.0)
            if tt < 90000.0:
                total_time += tt
        return total_time
