"""
City Graph Construction and Ephemeral State Builder.
Converts PostgreSQL PostGIS road network tables into a NetworkX directed graph.
Supports cloning for non-destructive, ephemeral scenario simulation.
"""
import copy
import logging
import networkx as nx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("citytwin.simulation.graph")

CITY_PROFILES = {
    3: {
        "name": "Lucknow",
        "roads": ["Hazratganj Main Corridor", "MG Marg Central", "Gomti Nagar Expressway", "Shaheed Path Outer Bypass", "Charbagh Station Link"],
        "base_capacity": 1400.0,
        "base_congestion": 0.18,
        "speed": 45.0,
    },
    1: {
        "name": "Chennai",
        "roads": ["Anna Salai Main Corridor", "Mount Road West", "OMR Tech Expressway", "GST Airport Connector"],
        "base_capacity": 1800.0,
        "base_congestion": 0.22,
        "speed": 50.0,
    },
    2: {
        "name": "Bengaluru",
        "roads": ["MG Road Central Corridor", "Outer Ring Road (ORR) Tech Line", "Hosur Road Expressway"],
        "base_capacity": 1200.0,
        "base_congestion": 0.35,
        "speed": 35.0,
    },
    4: {
        "name": "Mumbai",
        "roads": ["Western Express Highway (WEH)", "Bandra-Worli Sea Link", "Eastern Freeway Link"],
        "base_capacity": 2200.0,
        "base_congestion": 0.28,
        "speed": 55.0,
    },
    5: {
        "name": "Delhi NCR",
        "roads": ["Ring Road Central", "Outer Ring Road Express", "Delhi-Gurgaon Expressway"],
        "base_capacity": 2000.0,
        "base_congestion": 0.30,
        "speed": 52.0,
    },
    6: {
        "name": "Victoria / Melbourne",
        "roads": ["Flinders Street Central", "Monash Freeway Link", "CityLink Tollway Corridor"],
        "base_capacity": 1600.0,
        "base_congestion": 0.14,
        "speed": 60.0,
    },
}


class CityGraphBuilder:
    """Builds and manages NetworkX spatial graphs from PostGIS road networks."""

    @staticmethod
    def calculate_travel_time(length_m: float, speed_limit_kmh: float, congestion_level: float = 0.0) -> float:
        """
        Calculates travel time (seconds) along a road edge considering congestion.
        Formula: length / (effective_speed in m/s)
        """
        speed_limit_mps = max(speed_limit_kmh, 10.0) * (1000.0 / 3600.0)
        effective_speed_mps = speed_limit_mps * max(0.1, (1.0 - 0.85 * min(1.0, congestion_level)))
        return (length_m / effective_speed_mps)

    @classmethod
    def build_from_db(cls, db: Session, city_id: int) -> nx.DiGraph:
        """
        Queries roads and intersections from PostGIS for the specified city_id
        and constructs a directed NetworkX graph.
        """
        G = nx.DiGraph(city_id=city_id)

        try:
            # 1. Fetch nodes / intersections
            int_query = text("""
                SELECT intersection_id, ST_X(geometry) as x, ST_Y(geometry) as y
                FROM intersections
                WHERE city_id = :cid;
            """)
            nodes = db.execute(int_query, {"cid": city_id}).fetchall()
            for n in nodes:
                G.add_node(n.intersection_id, x=n.x, y=n.y)

            # 2. Fetch edges / roads
            road_query = text("""
                SELECT r.road_id, r.name, r.road_type, r.length_m, r.speed_limit, r.capacity, r.lanes,
                       COALESCE(t.congestion_level, 0.1) as congestion_level,
                       COALESCE(t.vehicle_count, 100) as vehicle_count
                FROM roads r
                LEFT JOIN (
                    SELECT DISTINCT ON (road_id) road_id, congestion_level, vehicle_count
                    FROM traffic_state
                    ORDER BY road_id, recorded_at DESC
                ) t ON r.road_id = t.road_id
                WHERE r.city_id = :cid;
            """)
            roads = db.execute(road_query, {"cid": city_id}).fetchall()

            node_ids = list(G.nodes)
            if not node_ids or len(roads) == 0:
                G = cls.build_synthetic_city_graph(city_id)
            else:
                for i, r in enumerate(roads):
                    u = node_ids[i % len(node_ids)]
                    v = node_ids[(i + 1) % len(node_ids)]
                    length = r.length_m or 500.0
                    speed = r.speed_limit or 50.0
                    tt = cls.calculate_travel_time(length, speed, r.congestion_level)
                    G.add_edge(u, v, road_id=r.road_id, name=r.name or f"Road {r.road_id}",
                               length_m=length, speed_limit=speed, capacity=r.capacity or 1000.0,
                               congestion_level=r.congestion_level, vehicle_count=r.vehicle_count,
                               travel_time=tt)
                    G.add_edge(v, u, road_id=r.road_id, name=r.name or f"Road {r.road_id} (Rev)",
                               length_m=length, speed_limit=speed, capacity=r.capacity or 1000.0,
                               congestion_level=r.congestion_level, vehicle_count=r.vehicle_count,
                               travel_time=tt)
        except Exception as exc:
            logger.warning("DB graph extraction failed (%s), generating fallback city graph for city_id=%d", str(exc), city_id)
            G = cls.build_synthetic_city_graph(city_id)

        if len(G.nodes) == 0:
            G = cls.build_synthetic_city_graph(city_id)

        return G

    @classmethod
    def build_synthetic_city_graph(cls, city_id: int) -> nx.DiGraph:
        """Generates a city-specific spatial graph with matching road IDs and parameters."""
        G = nx.grid_2d_graph(5, 5, create_using=nx.DiGraph)
        G.graph["city_id"] = city_id

        profile = CITY_PROFILES.get(city_id, CITY_PROFILES[3])
        road_names = profile["roads"]
        base_road_id = city_id * 100

        edge_index = 0
        for u, v in G.edges():
            edge_index += 1
            # First few edges get exact target road IDs matching frontend dropdown (e.g. 301, 302, 303...)
            if edge_index <= len(road_names):
                road_id = base_road_id + edge_index
                name = f"{road_names[edge_index - 1]} (#{road_id})"
            else:
                road_id = base_road_id + edge_index
                name = f"{profile['name']} Corridor #{road_id}"

            length = 500.0 + (edge_index * 20.0)
            speed = profile["speed"]
            congestion = profile["base_congestion"]
            capacity = profile["base_capacity"]
            tt = cls.calculate_travel_time(length, speed, congestion)

            G.edges[u, v].update({
                "road_id": road_id,
                "name": name,
                "length_m": length,
                "speed_limit": speed,
                "capacity": capacity,
                "congestion_level": congestion,
                "vehicle_count": int(capacity * congestion),
                "travel_time": tt
            })

        return G

    @staticmethod
    def create_ephemeral_copy(G: nx.DiGraph) -> nx.DiGraph:
        """
        Creates a deep ephemeral copy of the graph state.
        Guarantees hypothetical scenario simulations NEVER mutate the persistent state.
        """
        return copy.deepcopy(G)
