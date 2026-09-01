"""
Unit tests for Digital Twin Simulation Engine.
"""
from backend.app.simulation.engine import DigitalTwinEngine
from backend.app.simulation.graph import CityGraphBuilder
from backend.app.simulation.traffic import TrafficSimulator
from backend.app.simulation.transit import TransitSimulator
from backend.app.simulation.emergency import EmergencySimulator
from backend.app.simulation.pollution import PollutionEstimator


def test_traffic_simulator_rerouting():
    """Test road closure intervention rerouting on synthetic graph."""
    base_G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    ephemeral_G = CityGraphBuilder.create_ephemeral_copy(base_G)

    target_road_id = list(ephemeral_G.edges(data=True))[0][2]["road_id"]

    res = TrafficSimulator.apply_road_intervention(
        G=ephemeral_G,
        closed_road_id=target_road_id,
        capacity_factor=0.0,
        traffic_factor=1.0,
        weather_factor=1.0,
    )

    assert "baseline_congestion" in res
    assert "scenario_congestion" in res
    assert "change_percent" in res
    assert res["scenario_congestion"] >= res["baseline_congestion"]


def test_transit_simulator():
    """Test GTFS bus delay calculation across baseline vs scenario graphs."""
    base_G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    scenario_G = CityGraphBuilder.create_ephemeral_copy(base_G)

    # Increase travel times on scenario graph
    for u, v, d in scenario_G.edges(data=True):
        d["travel_time"] = d["travel_time"] * 1.5

    res = TransitSimulator.simulate_transit_delays(base_G, scenario_G)
    assert "delay_minutes" in res
    assert res["delay_minutes"] >= 0.0


def test_emergency_simulator():
    """Test emergency response ETA calculations."""
    base_G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    scenario_G = CityGraphBuilder.create_ephemeral_copy(base_G)

    for u, v, d in scenario_G.edges(data=True):
        d["travel_time"] = d["travel_time"] * 1.8

    res = EmergencySimulator.simulate_emergency_eta(base_G, scenario_G)
    assert "baseline_eta_min" in res
    assert "scenario_eta_min" in res
    assert res["scenario_eta_min"] >= res["baseline_eta_min"]


def test_pollution_estimator():
    """Test pollution impact estimation."""
    base_G = CityGraphBuilder.build_synthetic_city_graph(city_id=1)
    scenario_G = CityGraphBuilder.create_ephemeral_copy(base_G)

    res = PollutionEstimator.estimate_pollution_impact(base_G, scenario_G, weather_factor=1.2)
    assert "baseline_pollution_index" in res
    assert "scenario_pollution_index" in res
    assert "change_percent" in res
