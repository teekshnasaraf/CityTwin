"""Dependency-free synthetic traffic-state generator for ML development."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import random
from collections.abc import Iterable, Mapping

from .data_contract import TrafficStateRecord


@dataclass(frozen=True)
class RoadDefinition:
    road_id: str
    road_length: float
    lanes: int
    capacity: float

    def __post_init__(self) -> None:
        if not self.road_id:
            raise ValueError("road_id must not be empty")
        if self.road_length <= 0:
            raise ValueError("road_length must be positive")
        if self.lanes <= 0:
            raise ValueError("lanes must be positive")
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")


@dataclass(frozen=True)
class TrafficGenerationConfig:
    city_id: str = "synthetic-city"
    source: str = "synthetic_generator"
    quality_status: str = "development"
    free_flow_speed: float = 45.0
    minimum_speed: float = 5.0
    base_demand: float = 0.22
    morning_peak: float = 0.62
    midday_demand: float = 0.36
    evening_peak: float = 0.70
    night_demand: float = 0.10
    weekend_factor: float = 0.72
    rainfall_sensitivity: float = 0.12
    event_sensitivity: float = 0.20
    random_variation: float = 0.04


def generate_traffic_state(
    roads: Iterable[RoadDefinition | Mapping[str, object]],
    start_time: datetime,
    duration: timedelta,
    interval: timedelta,
    weather: Mapping[str, float] | None = None,
    event_factor: float = 0.0,
    seed: int | None = None,
    config: TrafficGenerationConfig | None = None,
) -> list[TrafficStateRecord]:
    """Generate explainable modelled traffic observations without persistence."""
    if not isinstance(start_time, datetime):
        raise TypeError("start_time must be a datetime")
    if duration <= timedelta(0) or interval <= timedelta(0):
        raise ValueError("duration and interval must be positive")
    if event_factor < 0:
        raise ValueError("event_factor must not be negative")

    settings = config or TrafficGenerationConfig()
    if settings.city_id == "":
        raise ValueError("city_id must not be empty")
    weather_values = weather or {}
    rainfall = float(weather_values.get("rainfall", 0.0))
    temperature = float(weather_values.get("temperature", 20.0))
    if rainfall < 0:
        raise ValueError("rainfall must not be negative")
    random_source = random.Random(seed)
    road_values = [_coerce_road(road) for road in roads]
    records: list[TrafficStateRecord] = []
    current_time = start_time
    end_time = start_time + duration

    while current_time < end_time:
        for road in road_values:
            demand = _demand_ratio(current_time, settings)
            weather_multiplier = max(0.0, 1.0 - settings.rainfall_sensitivity * rainfall)
            event_multiplier = 1.0 + settings.event_sensitivity * event_factor
            variation = 1.0 + random_source.uniform(-settings.random_variation, settings.random_variation)
            vehicle_count = max(0, round(road.capacity * demand * weather_multiplier * event_multiplier * variation))
            congestion = min(1.0, vehicle_count / road.capacity)
            speed_factor = max(0.0, 1.0 - 0.65 * congestion)
            average_speed = max(settings.minimum_speed, settings.free_flow_speed * speed_factor)
            records.append(
                TrafficStateRecord(
                    city_id=settings.city_id,
                    timestamp=current_time,
                    road_id=road.road_id,
                    vehicle_count=vehicle_count,
                    average_speed=average_speed,
                    road_capacity=road.capacity,
                    lanes=road.lanes,
                    road_length=road.road_length,
                    hour=current_time.hour,
                    day_of_week=current_time.weekday(),
                    rainfall=rainfall,
                    temperature=temperature,
                    event_factor=event_factor,
                    congestion=congestion,
                    source=settings.source,
                    data_type="MODELLED",
                    observed_at=current_time,
                    ingested_at=current_time,
                    quality_status=settings.quality_status,
                )
            )
        current_time += interval
    return records


def records_to_rows(records: Iterable[TrafficStateRecord]) -> list[dict[str, object]]:
    """Convert contract records to rows suitable for a future DataFrame."""
    return [record.as_dict() for record in records]


def _coerce_road(road: RoadDefinition | Mapping[str, object]) -> RoadDefinition:
    if isinstance(road, RoadDefinition):
        return road
    try:
        return RoadDefinition(
            road_id=str(road["road_id"]),
            road_length=float(road["road_length"]),
            lanes=int(road["lanes"]),
            capacity=float(road["capacity"]),
        )
    except KeyError as error:
        raise ValueError(f"road definition is missing {error.args[0]}") from error


def _demand_ratio(timestamp: datetime, settings: TrafficGenerationConfig) -> float:
    hour = timestamp.hour + timestamp.minute / 60
    if 7 <= hour < 10:
        ratio = settings.morning_peak
    elif 10 <= hour < 16:
        ratio = settings.midday_demand
    elif 16 <= hour < 20:
        ratio = settings.evening_peak
    elif hour < 6 or hour >= 22:
        ratio = settings.night_demand
    else:
        ratio = settings.base_demand
    if timestamp.weekday() >= 5:
        ratio *= settings.weekend_factor
    return max(0.0, ratio)