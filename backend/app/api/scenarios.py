"""
Scenario Management API Router.
Endpoints for defining and retrieving hypothetical city scenarios.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

try:
    from app.database import get_db
    from app.models.scenario import Scenario, ScenarioChange
except ImportError:
    from ..database import get_db
    from ..models.scenario import Scenario, ScenarioChange

router = APIRouter(prefix="/api/v1/scenarios", tags=["Scenarios"])


class ScenarioCreate(BaseModel):
    city_id: int
    name: str
    scenario_type: str = "road_closure"
    road_id: int
    duration_hours: float = 4.0
    capacity_factor: float = 0.0
    traffic_factor: float = 1.0
    weather_factor: float = 1.0


@router.post("", status_code=status.HTTP_201_CREATED)
def create_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    """Creates a new hypothetical scenario definition in the database."""
    scenario = Scenario(
        city_id=payload.city_id,
        name=payload.name,
        scenario_type=payload.scenario_type,
        created_by="user",
        created_at=datetime.utcnow(),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    change = ScenarioChange(
        scenario_id=scenario.scenario_id,
        road_id=payload.road_id,
        change_type=payload.scenario_type,
        capacity_factor=payload.capacity_factor,
        traffic_factor=payload.traffic_factor,
        weather_factor=payload.weather_factor,
    )
    db.add(change)
    db.commit()

    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "city_id": scenario.city_id,
        "created_at": scenario.created_at.isoformat(),
    }


@router.get("/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Retrieves scenario configuration details by scenario_id."""
    scenario = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    changes = db.query(ScenarioChange).filter(ScenarioChange.scenario_id == scenario_id).all()
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "scenario_type": scenario.scenario_type,
        "city_id": scenario.city_id,
        "created_at": scenario.created_at.isoformat(),
        "changes": [
            {
                "road_id": c.road_id,
                "change_type": c.change_type,
                "capacity_factor": c.capacity_factor,
                "traffic_factor": c.traffic_factor,
                "weather_factor": c.weather_factor,
            }
            for c in changes
        ],
    }
