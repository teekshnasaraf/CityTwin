"""
In-Memory NetworkX Spatial Graph Store & Graph RAG Extractor.
Replaces SQL table scans with sub-millisecond in-memory graph traversals and Graph RAG payloads for Groq LLM.
"""

import logging
import math
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple

try:
    from app.simulation.graph import CityGraphBuilder, CITY_PROFILES
except ImportError:
    from backend.app.simulation.graph import CityGraphBuilder, CITY_PROFILES

logger = logging.getLogger("citytwin.services.graph_store")


class InMemoryCityGraphStore:
    """Singleton In-Memory Graph Manager for high-speed spatial routing and LLM Graph RAG."""

    _instance: Optional["InMemoryCityGraphStore"] = None

    def __init__(self) -> None:
        self._graphs: Dict[int, nx.DiGraph] = {}
        self._initialize_default_city_graphs()

    @classmethod
    def get_instance(cls) -> "InMemoryCityGraphStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_city_graphs(self) -> None:
        """Pre-populates in-memory NetworkX graphs for all default cities."""
        for city_id in [1, 2, 3, 4, 5, 6]:
            self._graphs[city_id] = CityGraphBuilder.build_synthetic_city_graph(city_id)
        logger.info("Initialized In-Memory NetworkX Graph Store for %d cities.", len(self._graphs))

    def get_graph(self, city_id: int) -> nx.DiGraph:
        """Retrieves or builds the NetworkX spatial graph for a city."""
        if city_id not in self._graphs:
            self._graphs[city_id] = CityGraphBuilder.build_synthetic_city_graph(city_id)
        return self._graphs[city_id]

    def register_custom_city_graph(self, city_id: int, name: str, center_lat: float, center_lon: float) -> nx.DiGraph:
        """Dynamically generates and registers a spatial NetworkX graph for searched cities."""
        G = nx.grid_2d_graph(6, 6, create_using=nx.DiGraph)
        G.graph["city_id"] = city_id
        G.graph["name"] = name
        G.graph["center"] = (center_lat, center_lon)

        base_road_id = (city_id % 1000) * 100
        d_lat = 0.008
        d_lon = 0.008

        edge_counter = 0
        for u, v in G.edges():
            edge_counter += 1
            road_id = base_road_id + edge_counter
            
            # Compute actual geographic line coordinates
            u_lat = center_lat + (u[0] - 2.5) * d_lat
            u_lon = center_lon + (u[1] - 2.5) * d_lon
            v_lat = center_lat + (v[0] - 2.5) * d_lat
            v_lon = center_lon + (v[1] - 2.5) * d_lon

            name_str = f"{name.split(',')[0]} Corridor #{road_id}"
            length_m = 600.0 + (edge_counter * 15.0)

            G.nodes[u]["x"] = u_lon
            G.nodes[u]["y"] = u_lat
            G.nodes[v]["x"] = v_lon
            G.nodes[v]["y"] = v_lat

            G.edges[u, v].update({
                "road_id": road_id,
                "name": name_str,
                "length_m": length_m,
                "speed_limit": 50.0,
                "capacity": 1500.0,
                "congestion_level": 0.22,
                "vehicle_count": 330,
                "travel_time": length_m / (50.0 * (1000.0 / 3600.0)),
                "geometry": [[u_lat, u_lon], [(u_lat + v_lat) / 2.0, (u_lon + v_lon) / 2.0], [v_lat, v_lon]]
            })

        self._graphs[city_id] = G
        logger.info("Registered dynamic in-memory graph for city_id=%d (%s) with %d edges.", city_id, name, len(G.edges))
        return G

    def extract_subgraph_rag_payload(self, city_id: int, target_road_id: int, hop_radius: int = 2) -> Dict[str, Any]:
        """
        Extracts a 2-hop connected Graph RAG payload for Groq LLM context injection.
        Removes coordinate noise and provides pure topological adjacency and bottleneck metrics.
        """
        G = self.get_graph(city_id)
        
        target_edge = None
        target_nodes = None
        for u, v, data in G.edges(data=True):
            if data.get("road_id") == target_road_id:
                target_edge = data
                target_nodes = (u, v)
                break

        if not target_nodes:
            # Fallback to first edge if target road ID not matched
            u, v, data = list(G.edges(data=True))[0]
            target_edge = data
            target_nodes = (u, v)

        # Extract 2-hop ego subgraph
        ego_nodes = set(target_nodes)
        for _ in range(hop_radius):
            next_neighbors = set()
            for node in ego_nodes:
                next_neighbors.update(G.successors(node))
                next_neighbors.update(G.predecessors(node))
            ego_nodes.update(next_neighbors)

        subgraph_edges = []
        for u, v, data in G.edges(data=True):
            if u in ego_nodes and v in ego_nodes:
                subgraph_edges.append({
                    "road_id": data.get("road_id"),
                    "name": data.get("name"),
                    "capacity_veh_hr": data.get("capacity", 1500),
                    "baseline_congestion": data.get("congestion_level", 0.2),
                    "is_target_closed": (data.get("road_id") == target_road_id)
                })

        return {
            "city_id": city_id,
            "target_road": {
                "road_id": target_edge.get("road_id"),
                "name": target_edge.get("name"),
                "capacity": target_edge.get("capacity"),
                "status": "SIMULATED_CLOSED"
            },
            "subgraph_hop_radius": hop_radius,
            "connected_corridors_count": len(subgraph_edges),
            "connected_corridors": subgraph_edges[:15], # Subgraph RAG summary
            "graph_centrality_top_nodes": list(ego_nodes)[:6]
        }

    def export_graph_to_json(self, city_id: int) -> Dict[str, Any]:
        """Exports the in-memory NetworkX graph structure to JSON for frontend map plotting."""
        G = self.get_graph(city_id)
        
        nodes_list = []
        for node, data in G.nodes(data=True):
            nodes_list.append({
                "id": str(node),
                "lat": data.get("y", 26.8467),
                "lon": data.get("x", 80.9462)
            })

        edges_list = []
        for u, v, data in G.edges(data=True):
            u_lat = G.nodes[u].get("y", 26.8467)
            u_lon = G.nodes[u].get("x", 80.9462)
            v_lat = G.nodes[v].get("y", 26.8467)
            v_lon = G.nodes[v].get("x", 80.9462)

            geom = data.get("geometry") or [[u_lat, u_lon], [(u_lat + v_lat)/2.0, (u_lon + v_lon)/2.0], [v_lat, v_lon]]
            edges_list.append({
                "road_id": data.get("road_id"),
                "name": data.get("name"),
                "length_m": data.get("length_m", 500.0),
                "capacity": data.get("capacity", 1500.0),
                "congestion_level": data.get("congestion_level", 0.2),
                "path": geom
            })

        return {
            "city_id": city_id,
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "nodes": nodes_list,
            "edges": edges_list
        }


graph_store = InMemoryCityGraphStore.get_instance()
