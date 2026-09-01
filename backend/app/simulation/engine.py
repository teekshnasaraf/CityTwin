"""
Digital Twin Core Simulation Orchestrator.
Loads current PostGIS city state into an ephemeral NetworkX graph,
applies hypothetical scenario modifications, and executes cascading simulation engines
(Traffic Rerouting, GTFS Bus Delays, Emergency Response ETAs, Pollution Impact).
Guarantees database non-destructiveness.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.simulation.graph import CityGraphBuilder
from app.simulation.traffic import TrafficSimulator
from app.simulation.transit import TransitSimulator
from app.simulation.emergency import EmergencySimulator
from app.simulation.pollution import PollutionEstimator

logger = logging.getLogger("citytwin.simulation.engine")


class DigitalTwinEngine:
    """Orchestrates cascading simulation runs on ephemeral city graph state."""

    @classmethod
    def run_scenario_simulation(
        cls,
        db: Session,
        city_id: int,
        closed_road_id: int,
        duration_hours: float = 4.0,
        capacity_factor: float = 0.0,
        traffic_factor: float = 1.0,
        weather_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end cascading simulation run.

        Parameters:
            db: SQLAlchemy Database Session
            city_id: Target city ID
            closed_road_id: Target road segment ID
            duration_hours: Intervention duration
            capacity_factor: 0.0 for total closure, 0.5 for partial closure
            traffic_factor: Traffic multiplier (e.g. 1.1 for +10%)
            weather_factor: Weather multiplier (e.g. 1.2 for +20% rain)

        Returns:
            Dict containing traffic, transit, emergency, and pollution metrics.
        """
        logger.info(
            "Starting Digital Twin simulation: city_id=%d, road_id=%d, cap_factor=%.2f",
            city_id, closed_road_id, capacity_factor
        )

        # 1. Build base graph from DB
        base_graph = CityGraphBuilder.build_from_db(db, city_id)

        # 2. Create EPHEMERAL graph copy for simulation (Non-destructive to DB!)
        scenario_graph = CityGraphBuilder.create_ephemeral_copy(base_graph)

        # 3. Run Traffic Simulation & Rerouting
        traffic_results = TrafficSimulator.apply_road_intervention(
            G=scenario_graph,
            closed_road_id=closed_road_id,
            capacity_factor=capacity_factor,
            traffic_factor=traffic_factor,
            weather_factor=weather_factor,
        )

        # 4. Run Public Transit Delay Simulation
        transit_results = TransitSimulator.simulate_transit_delays(
            baseline_graph=base_graph, scenario_graph=scenario_graph
        )

        # 5. Run Emergency Response ETA Simulation
        emergency_results = EmergencySimulator.simulate_emergency_eta(
            baseline_graph=base_graph, scenario_graph=scenario_graph
        )

        # 6. Run Pollution Impact Estimation
        pollution_results = PollutionEstimator.estimate_pollution_impact(
            baseline_graph=base_graph, scenario_graph=scenario_graph, weather_factor=weather_factor
        )

        # Compile metrics list
        metrics = [
            {
                "metric_type": "traffic_congestion",
                "baseline_value": traffic_results["baseline_congestion"],
                "scenario_value": traffic_results["scenario_congestion"],
                "change_percent": traffic_results["change_percent"],
                "unit": "congestion_index",
            },
            {
                "metric_type": "bus_delay",
                "baseline_value": transit_results["baseline_transit_time_min"],
                "scenario_value": transit_results["scenario_transit_time_min"],
                "change_percent": transit_results["change_percent"],
                "unit": "minutes",
            },
            {
                "metric_type": "emergency_eta",
                "baseline_value": emergency_results["baseline_eta_min"],
                "scenario_value": emergency_results["scenario_eta_min"],
                "change_percent": emergency_results["change_percent"],
                "unit": "minutes",
            },
            {
                "metric_type": "pollution",
                "baseline_value": pollution_results["baseline_pollution_index"],
                "scenario_value": pollution_results["scenario_pollution_index"],
                "change_percent": pollution_results["change_percent"],
                "unit": "emission_index",
            },
        ]

        return {
            "city_id": city_id,
            "closed_road_id": closed_road_id,
            "duration_hours": duration_hours,
            "traffic": traffic_results,
            "transit": transit_results,
            "emergency": emergency_results,
            "pollution": pollution_results,
            "metrics": metrics,
        }
