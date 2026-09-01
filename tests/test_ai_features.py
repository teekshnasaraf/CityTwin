import math
import unittest
from datetime import datetime, timedelta

from backend.app.ai.data_contract import TrafficStateRecord
from backend.app.ai.features import (
    MODEL_FEATURE_NAMES,
    build_training_samples,
    extract_features,
    split_features_and_target,
)


def traffic_record(road_id: str, timestamp: datetime, vehicle_count: int, data_type: str = "MODELLED") -> TrafficStateRecord:
    return TrafficStateRecord(
        city_id="synthetic-city",
        timestamp=timestamp,
        road_id=road_id,
        vehicle_count=vehicle_count,
        average_speed=30.0,
        road_capacity=1200.0,
        lanes=2,
        road_length=500.0,
        hour=timestamp.hour,
        day_of_week=timestamp.weekday(),
        rainfall=2.0,
        temperature=24.0,
        event_factor=0.1,
        congestion=vehicle_count / 1200,
        source="synthetic_generator",
        data_type=data_type,
        observed_at=timestamp,
        ingested_at=timestamp,
        quality_status="development",
    )


class TrafficFeatureTests(unittest.TestCase):
    def test_extracts_features_and_cyclical_time_values(self) -> None:
        record = traffic_record("road_001", datetime(2026, 1, 5, 6), 500)

        features = extract_features(record)

        self.assertEqual(set(MODEL_FEATURE_NAMES), set(features))
        self.assertAlmostEqual(1.0, features["hour_sin"])
        self.assertAlmostEqual(0.0, features["hour_cos"])
        day_angle = 2 * math.pi * record.day_of_week / 7
        self.assertAlmostEqual(math.sin(day_angle), features["day_of_week_sin"])
        self.assertAlmostEqual(math.cos(day_angle), features["day_of_week_cos"])

    def test_aligns_target_by_same_road_and_exact_horizon(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        records = [
            traffic_record("road_001", current_time, 700),
            traffic_record("road_001", current_time + timedelta(minutes=15), 760),
        ]

        samples = build_training_samples(records)

        self.assertEqual(1, len(samples))
        self.assertEqual(760, samples[0].target_vehicle_count)
        self.assertEqual(current_time + timedelta(minutes=15), samples[0].future_timestamp)

    def test_multiple_roads_pair_independently(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        records = [
            traffic_record("road_001", current_time, 700),
            traffic_record("road_002", current_time, 300),
            traffic_record("road_001", current_time + timedelta(minutes=15), 760),
            traffic_record("road_002", current_time + timedelta(minutes=15), 360),
        ]

        samples = build_training_samples(records)

        self.assertEqual({("road_001", 760), ("road_002", 360)}, {(sample.road_id, sample.target()) for sample in samples})

    def test_missing_or_wrong_timestamp_is_skipped(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        records = [
            traffic_record("road_001", current_time, 700),
            traffic_record("road_001", current_time + timedelta(minutes=10), 740),
            traffic_record("road_002", current_time, 300),
        ]

        self.assertEqual([], build_training_samples(records))

    def test_target_is_not_in_feature_row_and_identifiers_are_separate(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        samples = build_training_samples(
            [
                traffic_record("road_001", current_time, 700),
                traffic_record("road_001", current_time + timedelta(minutes=15), 760),
            ]
        )

        features, targets = split_features_and_target(samples)

        self.assertNotIn("target_vehicle_count", features[0])
        self.assertNotIn("road_id", features[0])
        self.assertNotIn("timestamp", features[0])
        self.assertEqual([760], targets)
        self.assertEqual("road_001", samples[0].road_id)
        self.assertEqual(current_time, samples[0].timestamp)

    def test_configurable_horizon(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        records = [
            traffic_record("road_001", current_time, 700),
            traffic_record("road_001", current_time + timedelta(minutes=30), 800),
        ]

        samples = build_training_samples(records, horizon_minutes=30)

        self.assertEqual([800], [sample.target() for sample in samples])

    def test_prediction_and_scenario_records_are_not_training_inputs(self) -> None:
        current_time = datetime(2026, 1, 5, 8)
        records = [
            traffic_record("road_001", current_time, 700, data_type="PREDICTED"),
            traffic_record("road_001", current_time + timedelta(minutes=15), 760),
            traffic_record("road_002", current_time, 300, data_type="SCENARIO"),
            traffic_record("road_002", current_time + timedelta(minutes=15), 360),
        ]

        self.assertEqual([], build_training_samples(records))


if __name__ == "__main__":
    unittest.main()