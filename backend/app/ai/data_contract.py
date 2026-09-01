"""Validated traffic-state records shared by data producers and ML consumers."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


SUPPORTED_DATA_TYPES = frozenset({"REALTIME", "HISTORICAL", "MODELLED", "PREDICTED", "SCENARIO"})


@dataclass(frozen=True)
class TrafficStateRecord:
    city_id: str
    timestamp: datetime
    road_id: str
    vehicle_count: int
    average_speed: float
    road_capacity: float
    lanes: int
    road_length: float
    hour: int
    day_of_week: int
    rainfall: float
    temperature: float
    event_factor: float
    congestion: float
    source: str
    data_type: str
    observed_at: datetime
    ingested_at: datetime
    quality_status: str
    source_record_id: str | None = None

    VALID_CONGESTION_RANGE: ClassVar[tuple[float, float]] = (0.0, 1.0)

    def __post_init__(self) -> None:
        if not self.city_id or not self.road_id:
            raise ValueError("city_id and road_id must not be empty")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        if not isinstance(self.observed_at, datetime) or not isinstance(self.ingested_at, datetime):
            raise TypeError("observed_at and ingested_at must be datetimes")
        if self.vehicle_count < 0:
            raise ValueError("vehicle_count must not be negative")
        if self.average_speed < 0:
            raise ValueError("average_speed must not be negative")
        if self.road_capacity <= 0:
            raise ValueError("road_capacity must be positive")
        if self.lanes <= 0:
            raise ValueError("lanes must be positive")
        if self.road_length <= 0:
            raise ValueError("road_length must be positive")
        if self.hour not in range(24):
            raise ValueError("hour must be between 0 and 23")
        if self.day_of_week not in range(7):
            raise ValueError("day_of_week must be between 0 and 6")
        if self.rainfall < 0:
            raise ValueError("rainfall must not be negative")
        if not self.VALID_CONGESTION_RANGE[0] <= self.congestion <= self.VALID_CONGESTION_RANGE[1]:
            raise ValueError("congestion must be between 0 and 1")
        if self.data_type not in SUPPORTED_DATA_TYPES:
            raise ValueError(f"data_type must be one of {sorted(SUPPORTED_DATA_TYPES)}")

    def as_dict(self) -> dict[str, object]:
        """Return the contract as a flat, tabular-friendly mapping."""
        return {
            "timestamp": self.timestamp,
            "city_id": self.city_id,
            "road_id": self.road_id,
            "vehicle_count": self.vehicle_count,
            "average_speed": self.average_speed,
            "road_capacity": self.road_capacity,
            "lanes": self.lanes,
            "road_length": self.road_length,
            "hour": self.hour,
            "day_of_week": self.day_of_week,
            "rainfall": self.rainfall,
            "temperature": self.temperature,
            "event_factor": self.event_factor,
            "congestion": self.congestion,
            "source": self.source,
            "source_record_id": self.source_record_id,
            "observed_at": self.observed_at,
            "ingested_at": self.ingested_at,
            "quality_status": self.quality_status,
            "data_type": self.data_type,
        }