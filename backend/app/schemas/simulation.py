"""
Pydantic Schemas for Scenarios, Simulation Execution, Metrics, and Recommendations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SimulationRunRequest(BaseModel):
    city_id: int = Field(default=1, description="Target city ID")
    closed_road_id: int = Field(default=101, description="Target road segment ID")
    duration_hours: float = Field(default=4.0, ge=0.5, le=48.0)
    capacity_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    traffic_factor: float = Field(default=1.0, ge=0.5, le=3.0)
    weather_factor: float = Field(default=1.0, ge=0.5, le=3.0)


class SimulationMetricItem(BaseModel):
    metric_type: str
    baseline_value: float
    scenario_value: float
    change_percent: float
    unit: str


class SimulationRunResponse(BaseModel):
    run_id: Optional[int] = None
    city_id: int
    closed_road_id: int
    duration_hours: float
    traffic: Dict[str, Any]
    transit: Dict[str, Any]
    emergency: Dict[str, Any]
    pollution: Dict[str, Any]
    metrics: List[SimulationMetricItem]


class RecommendationItem(BaseModel):
    rank: int
    intervention: str
    score: float
    reason: str
    simulation: Optional[Dict[str, Any]] = None


class RecommendationEvaluationResponse(BaseModel):
    city_id: int
    closed_road_id: int
    weights: Dict[str, float]
    best_option: str
    best_score: float
    recommendations: List[RecommendationItem]
