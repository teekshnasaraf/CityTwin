"""
Unit tests for In-Memory NetworkX Spatial Graph Store and Graph RAG Extractor.
"""
import pytest
from backend.app.services.graph_store import InMemoryCityGraphStore, graph_store


def test_in_memory_graph_store_retrieval():
    """Verify in-memory NetworkX graph retrieval for default cities."""
    G_lucknow = graph_store.get_graph(city_id=3)
    assert len(G_lucknow.nodes) == 25
    assert len(G_lucknow.edges) > 0
    assert G_lucknow.graph["city_id"] == 3


def test_graph_export_to_json():
    """Verify export of NetworkX spatial graph to JSON for Leaflet GIS rendering."""
    json_data = graph_store.export_graph_to_json(city_id=3)
    assert json_data["city_id"] == 3
    assert json_data["total_nodes"] == 25
    assert len(json_data["edges"]) > 0
    assert "road_id" in json_data["edges"][0]
    assert "path" in json_data["edges"][0]


def test_graph_rag_subgraph_extraction():
    """Verify 2-hop connected Graph RAG payload extraction for Groq LLM."""
    rag_payload = graph_store.extract_subgraph_rag_payload(city_id=3, target_road_id=301, hop_radius=2)
    assert rag_payload["city_id"] == 3
    assert rag_payload["target_road"]["road_id"] == 301
    assert rag_payload["connected_corridors_count"] > 0
    assert len(rag_payload["connected_corridors"]) > 0


def test_register_dynamic_city_graph():
    """Verify dynamic graph creation for searched cities."""
    G_custom = graph_store.register_custom_city_graph(
        city_id=999,
        name="Gandhinagar, India",
        center_lat=23.2156,
        center_lon=72.6369
    )
    assert G_custom.graph["city_id"] == 999
    assert G_custom.graph["name"] == "Gandhinagar, India"
    assert len(G_custom.nodes) == 36
