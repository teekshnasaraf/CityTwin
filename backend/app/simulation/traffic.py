"""
Traffic Simulation & Rerouting Engine.
Computes origin-destination traffic redistribution, dynamic congestion levels,
and travel time deltas when road network capacities change.
"""
import logging
import networkx as nx
from typing import Dict, Any, List, Tuple
from app.simulation.graph import CityGraphBuilder

logger = logging.getLogger("citytwin.simulation.traffic")


class TrafficSimulator:
    """Executes traffic routing, volume redistribution, and congestion calculations."""

    @staticmethod
    def find_edges_by_road_id(G: nx.DiGraph, road_id: int) -> List[Tuple[Any, Any]]:
        """Finds graph edge tuple(s) matching a given road_id."""
        matching_edges = []
        for u, v, data in G.edges(data=True):
            if data.get("road_id") == road_id:
                matching_edges.append((u, v))
        return matching_edges

    @classmethod
    def apply_road_intervention(
        cls,
        G: nx.DiGraph,
        closed_road_id: int,
        capacity_factor: float = 0.0,
        traffic_factor: float = 1.0,
        weather_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Applies road intervention to an ephemeral copy of the city graph,
        reroutes traffic, and returns performance deltas.
        """
        # 1. Calculate baseline metrics
        baseline_tt, baseline_congestion = cls._compute_network_summary(G)

        # 2. Locate targeted edge(s)
        target_edges = cls.find_edges_by_road_id(G, closed_road_id)
        if not target_edges and len(G.edges) > 0:
            # Fallback to first edge if specific road_id not matched
            target_edges = [list(G.edges)[0]]

        affected_volume = 0
        for u, v in target_edges:
            edge_data = G.edges[u, v]
            affected_volume += edge_data.get("vehicle_count", 200)
            edge_data["capacity"] = max(1.0, edge_data.get("capacity", 1000.0) * capacity_factor)
            if capacity_factor == 0.0:
                edge_data["congestion_level"] = 1.0
                edge_data["travel_time"] = 99999.0  # Closed road penalty
            else:
                edge_data["congestion_level"] = min(1.0, edge_data.get("congestion_level", 0.2) / max(0.1, capacity_factor))
                edge_data["travel_time"] = CityGraphBuilder.calculate_travel_time(
                    edge_data["length_m"], edge_data["speed_limit"], edge_data["congestion_level"]
                )

        # 3. Reroute displaced traffic onto remaining graph edges
        if affected_volume > 0 and len(G.edges) > len(target_edges):
            displaced_per_edge = (affected_volume * traffic_factor * weather_factor) / (len(G.edges) - len(target_edges))
            for u, v, data in G.edges(data=True):
                if (u, v) not in target_edges:
                    data["vehicle_count"] = data.get("vehicle_count", 200) + int(displaced_per_edge)
                    # Congestion increases proportionally with added volume vs capacity
                    volume_ratio = data["vehicle_count"] / max(1.0, data.get("capacity", 1000.0))
                    data["congestion_level"] = min(0.95, data.get("congestion_level", 0.1) + 0.3 * volume_ratio)
                    data["travel_time"] = CityGraphBuilder.calculate_travel_time(
                        data["length_m"], data["speed_limit"], data["congestion_level"]
                    )

        # 4. Calculate scenario metrics
        scenario_tt, scenario_congestion = cls._compute_network_summary(G)
        pct_change = ((scenario_congestion - baseline_congestion) / max(0.01, baseline_congestion)) * 100.0

        return {
            "baseline_congestion": round(baseline_congestion, 4),
            "scenario_congestion": round(scenario_congestion, 4),
            "change_percent": round(pct_change, 2),
            "baseline_travel_time_s": round(baseline_tt, 2),
            "scenario_travel_time_s": round(scenario_tt, 2),
        }

    @staticmethod
    def _compute_network_summary(G: nx.DiGraph) -> Tuple[float, float]:
        """Computes average network travel time and congestion level."""
        if not G.edges:
            return 0.0, 0.0

        valid_tts = [d.get("travel_time", 60.0) for u, v, d in G.edges(data=True) if d.get("travel_time", 0) < 90000.0]
        congestions = [d.get("congestion_level", 0.1) for u, v, d in G.edges(data=True)]

        avg_tt = sum(valid_tts) / max(1, len(valid_tts)) if valid_tts else 60.0
        avg_cg = sum(congestions) / max(1, len(congestions)) if congestions else 0.1
        return avg_tt, avg_cg
