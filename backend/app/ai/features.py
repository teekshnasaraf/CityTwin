"""Feature engineering for short-horizon traffic prediction."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from collections.abc import Iterable, Mapping

from .data_contract import TrafficStateRecord


MODEL_FEATURE_NAMES = (
    "vehicle_count",
    "average_speed",
    "road_capacity",
    "lanes",
    "road_length",
    "congestion",
    "hour",
    "day_of_week",
    "rainfall",
    "temperature",
    "event_factor",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
)
TRAINING_DATA_TYPES = frozenset({"REALTIME", "HISTORICAL", "MODELLED"})


@dataclass(frozen=True)
class TrafficTrainingSample:
    """One current-state feature row paired with a future same-road target."""

    road_id: str
    timestamp: datetime
    features: Mapping[str, float | int]
    target_vehicle_count: int
    source: str
    data_type: str
    future_timestamp: datetime
    future_source: str
    future_data_type: str

    def __post_init__(self) -> None:
        missing = set(MODEL_FEATURE_NAMES) - set(self.features)
        if missing:
            raise ValueError(f"features are missing {sorted(missing)}")
        unexpected = set(self.features) - set(MODEL_FEATURE_NAMES)
        if unexpected:
            raise ValueError(f"features contain unsupported fields {sorted(unexpected)}")
        if self.target_vehicle_count < 0:
            raise ValueError("target_vehicle_count must not be negative")
        if not isinstance(self.timestamp, datetime) or not isinstance(self.future_timestamp, datetime):
            raise TypeError("timestamp fields must be datetimes")

    def feature_row(self) -> dict[str, float | int]:
        """Return only numerical model inputs, excluding identifiers and target."""
        return dict(self.features)

    def target(self) -> int:
        return self.target_vehicle_count


def build_training_samples(
    records: Iterable[TrafficStateRecord],
    horizon_minutes: int = 15,
) -> list[TrafficTrainingSample]:
    """Pair each eligible current record with an exact future same-road record."""
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")
    horizon = timedelta(minutes=horizon_minutes)
    indexed_records: dict[tuple[str, datetime], TrafficStateRecord] = {}
    record_values = list(records)
    for record in record_values:
        _validate_record(record)
        if record.data_type not in TRAINING_DATA_TYPES:
            continue
        key = (record.road_id, record.timestamp)
        if key in indexed_records:
            raise ValueError(f"duplicate traffic record for {record.road_id} at {record.timestamp}")
        indexed_records[key] = record

    samples: list[TrafficTrainingSample] = []
    for current in record_values:
        if current.data_type not in TRAINING_DATA_TYPES:
            continue
        future_timestamp = current.timestamp + horizon
        future = indexed_records.get((current.road_id, future_timestamp))
        if future is None:
            continue
        samples.append(
            TrafficTrainingSample(
                road_id=current.road_id,
                timestamp=current.timestamp,
                features=extract_features(current),
                target_vehicle_count=future.vehicle_count,
                source=current.source,
                data_type=current.data_type,
                future_timestamp=future.timestamp,
                future_source=future.source,
                future_data_type=future.data_type,
            )
        )
    return samples


def extract_features(record: TrafficStateRecord) -> dict[str, float | int]:
    """Extract baseline current-state features from one traffic record."""
    _validate_record(record)
    hour_angle = 2 * math.pi * record.hour / 24
    day_angle = 2 * math.pi * record.day_of_week / 7
    return {
        "vehicle_count": record.vehicle_count,
        "average_speed": record.average_speed,
        "road_capacity": record.road_capacity,
        "lanes": record.lanes,
        "road_length": record.road_length,
        "congestion": record.congestion,
        "hour": record.hour,
        "day_of_week": record.day_of_week,
        "rainfall": record.rainfall,
        "temperature": record.temperature,
        "event_factor": record.event_factor,
        "hour_sin": math.sin(hour_angle),
        "hour_cos": math.cos(hour_angle),
        "day_of_week_sin": math.sin(day_angle),
        "day_of_week_cos": math.cos(day_angle),
    }


def split_features_and_target(
    samples: Iterable[TrafficTrainingSample],
) -> tuple[list[dict[str, float | int]], list[int]]:
    """Return model input rows and targets in matching order."""
    sample_values = list(samples)
    return [sample.feature_row() for sample in sample_values], [sample.target() for sample in sample_values]


def _validate_record(record: TrafficStateRecord) -> None:
    if not isinstance(record, TrafficStateRecord):
        raise TypeError("records must contain TrafficStateRecord values")
    numeric_values = (
        record.vehicle_count,
        record.average_speed,
        record.road_capacity,
        record.lanes,
        record.road_length,
        record.hour,
        record.day_of_week,
        record.rainfall,
        record.temperature,
        record.event_factor,
        record.congestion,
    )
    if not all(math.isfinite(float(value)) for value in numeric_values):
        raise ValueError("traffic record contains a non-finite numeric value")