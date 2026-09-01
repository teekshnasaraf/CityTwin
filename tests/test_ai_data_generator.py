import unittest
from datetime import datetime, timedelta

from backend.app.ai.data_contract import TrafficStateRecord
from backend.app.ai.data_generator import generate_traffic_state, records_to_rows


ROADS = [
    {"road_id": "road_001", "road_length": 800, "lanes": 3, "capacity": 1800},
    {"road_id": "road_002", "road_length": 500, "lanes": 2, "capacity": 1200},
]


class TrafficGeneratorTests(unittest.TestCase):
    def test_generates_valid_modelled_records_for_generic_roads(self) -> None:
        records = generate_traffic_state(
            ROADS,
            datetime(2026, 1, 5, 8),
            timedelta(hours=1),
            timedelta(minutes=30),
            seed=7,
        )

        self.assertEqual(4, len(records))
        self.assertTrue(all(isinstance(record, TrafficStateRecord) for record in records))
        self.assertTrue(all(record.data_type == "MODELLED" for record in records))
        self.assertTrue(all(record.vehicle_count >= 0 for record in records))
        self.assertTrue(all(0 <= record.congestion <= 1 for record in records))
        self.assertEqual({"road_001", "road_002"}, {record.road_id for record in records})
        self.assertEqual(len(records), len(records_to_rows(records)))

    def test_peak_differs_from_low_demand(self) -> None:
        peak = generate_traffic_state(ROADS[:1], datetime(2026, 1, 5, 8), timedelta(hours=1), timedelta(hours=1), seed=1)
        night = generate_traffic_state(ROADS[:1], datetime(2026, 1, 2, 23), timedelta(hours=1), timedelta(hours=1), seed=1)

        self.assertGreater(peak[0].vehicle_count, night[0].vehicle_count)

    def test_seed_is_reproducible(self) -> None:
        arguments = (ROADS, datetime(2026, 1, 5, 8), timedelta(hours=2), timedelta(hours=1))
        first = generate_traffic_state(*arguments, seed=11)
        second = generate_traffic_state(*arguments, seed=11)

        self.assertEqual(first, second)

    def test_contract_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            TrafficStateRecord(
                city_id="city",
                timestamp=datetime.now(),
                road_id="road",
                vehicle_count=-1,
                average_speed=1,
                road_capacity=1,
                lanes=1,
                road_length=1,
                hour=0,
                day_of_week=0,
                rainfall=0,
                temperature=20,
                event_factor=0,
                congestion=0,
                source="test",
                data_type="MODELLED",
                observed_at=datetime.now(),
                ingested_at=datetime.now(),
                quality_status="test",
            )


if __name__ == "__main__":
    unittest.main()