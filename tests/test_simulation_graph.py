"""
Unit tests for Simulation Graph Construction and Ephemeral Isolation.
"""
import pytest
import networkx as nx
from backend.app.simulation.graph import CityGraphBuilder


def test_calculate_travel_time():
    """Verify edge travel time calculations under baseline and congested conditions."""
    # 600m at 60km/h (16.66 m/s) with 0 congestion -> 36 seconds
    tt_baseline = CityGraphBuilder.calculate_travel_time(600.0, 60.0, congestion_level=0.0)
    assert round(tt_baseline, 1) == 36.0

    # 600m at 60km/h with 0.5 congestion level -> effective speed drops, travel time increases
    tt_congested = CityGraphBuilder.calculate_travel_time(600.0, 60.0, congestion_level=0.5)
    assert tt_congested > tt_baseline


def test_synthetic_graph_building():
    """Verify synthetic grid city graph structure."""
    G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    assert len(G.nodes) == 25  # 5x5 grid
    assert len(G.edges) > 0
    assert G.graph["city_id"] == 1

    # Check edge attributes
    edge = list(G.edges(data=True))[0]
    data = edge[2]
    assert "road_id" in data
    assert "travel_time" in data
    assert "capacity" in data


def test_ephemeral_copy_isolation():
    """Verify that mutating an ephemeral graph copy does not alter the base graph."""
    base_G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    ephemeral_G = CityGraphBuilder.create_ephemeral_copy(base_G)

    # Mutate edge in ephemeral copy
    u, v = list(ephemeral_G.edges)[0]
    original_cap = base_G.edges[u, v]["capacity"]
    original_cong = base_G.edges[u, v]["congestion_level"]

    ephemeral_G.edges[u, v]["capacity"] = 0.0
    ephemeral_G.edges[u, v]["congestion_level"] = 1.0

    # Verify base graph is completely unchanged (Rule 12 & Rule 25)
    assert base_G.edges[u, v]["capacity"] == original_cap
    assert base_G.edges[u, v]["congestion_level"] == original_cong
    assert base_G.edges[u, v]["capacity"] != ephemeral_G.edges[u, v]["capacity"]
