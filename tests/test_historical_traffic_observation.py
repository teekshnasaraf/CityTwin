import csv
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
import zipfile

from backend.app.ingestion.traffic.historical_observation import (
    DEFAULT_TIMEZONE,
    HistoricalTrafficObservation,
    VictoriaSchemaError,
    load_historical_observations,
)


TRAFFIC_HEADER = ["date", "time_bin", "site", "heading", "vehicle_class", "speed_bin", "volume"]


class HistoricalTrafficObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.sites_path = root / "telemetry_sites.csv"
        with self.sites_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["site", "site_description", "latitude", "longitude"])
            writer.writerow(["10001", "Test north", "-37.2", "145.0"])
            writer.writerow(["10002", "Test south", "-37.3", "145.1"])

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write_csv(self, name: str, rows: list[list[str]]) -> Path:
        path = Path(self.directory.name) / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(TRAFFIC_HEADER)
            writer.writerows(rows)
        return path

    def test_csv_parsing_aggregation_and_metadata(self) -> None:
        csv_path = self.write_csv(
            "june.csv",
            [
                ["2026-06-01", "10:00", "10001", "North", "4bin: 1.Short", "90km/hr to < 95km/hr", "10"],
                ["2026-06-01", "10:00", "10001", "North", "4bin: 1.Short", "95km/hr to < 100km/hr", "15"],
                ["2026-06-01", "10:00", "10001", "North", "4bin: 2.Rigid", "90km/hr to < 95km/hr", "20"],
                ["2026-06-01", "10:00", "10001", "South", "Other", "0km/hr to < 5km/hr", "7"],
            ],
        )

        batch = load_historical_observations(csv_path, self.sites_path)

        north = batch.observations[0]
        self.assertIsInstance(north, HistoricalTrafficObservation)
        self.assertEqual(45, north.vehicle_count)
        self.assertEqual("10001", north.site_id)
        self.assertEqual("North", north.heading)
        self.assertEqual(datetime(2026, 6, 1, 10, tzinfo=north.timestamp.tzinfo), north.timestamp)
        self.assertEqual(DEFAULT_TIMEZONE, north.timestamp.tzinfo.key)
        self.assertEqual((-37.2, 145.0), (north.latitude, north.longitude))
        self.assertEqual("HISTORICAL", north.data_type)
        self.assertEqual(4, batch.stats.valid_rows)
        self.assertNotIn("average_speed", north.__dict__)
        self.assertTrue(north.sensor_identifier.startswith("vic_sensor_"))
        self.assertNotIn("osm", north.sensor_identifier.lower())

    def test_zip_and_multiple_inputs_are_supported(self) -> None:
        first = self.write_csv("july.csv", [["2026-07-01", "10:00", "10001", "North", "4bin", "90km/hr to < 95km/hr", "3"]])
        second = self.write_csv("august.csv", [["2026-08-01", "10:15", "10002", "South", "12bin", "95km/hr to < 100km/hr", "4"]])
        archive_path = Path(self.directory.name) / "july.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(first, "TELEMETRYDATA_20260701.csv")
        batch = load_historical_observations([archive_path, second], self.sites_path)

        self.assertEqual(2, len(batch.observations))
        self.assertEqual(2, batch.stats.csv_members_processed)
        self.assertEqual({"10001", "10002"}, {item.site_id for item in batch.observations})
        self.assertEqual(4, batch.observations[1].vehicle_count)

    def test_class_and_speed_bin_structures_are_preserved(self) -> None:
        csv_path = self.write_csv(
            "classes.csv",
            [
                ["2026-06-01", "10:00", "10001", "North", "4bin: 1.Short", "90km/hr to < 95km/hr", "2"],
                ["2026-06-01", "10:00", "10001", "North", "12bin: 10.B Double", "100km/hr to < 105km/hr", "5"],
                ["2026-06-01", "10:00", "10001", "North", "Other", "150km/hr +", "1"],
            ],
        )

        observation = load_historical_observations(csv_path, self.sites_path).observations[0]

        self.assertEqual({"4bin: 1.Short": 2, "12bin: 10.B Double": 5, "Other": 1}, observation.vehicle_class_counts)
        self.assertEqual({"90km/hr to < 95km/hr": 2, "100km/hr to < 105km/hr": 5, "150km/hr +": 1}, observation.speed_bin_counts)

    def test_invalid_rows_are_skipped_and_t15_is_not_interpolated(self) -> None:
        csv_path = self.write_csv(
            "invalid.csv",
            [
                ["2026-06-01", "10:00", "10001", "North", "4bin", "90km/hr to < 95km/hr", "2"],
                ["not-a-date", "10:15", "10001", "North", "4bin", "90km/hr to < 95km/hr", "3"],
                ["2026-06-01", "10:30", "10001", "North", "4bin", "90km/hr to < 95km/hr", ""],
                ["2026-06-01", "10:45", "99999", "North", "4bin", "90km/hr to < 95km/hr", "4"],
            ],
        )

        batch = load_historical_observations(csv_path, self.sites_path)

        self.assertEqual(1, len(batch.observations))
        self.assertEqual(3, batch.stats.skipped_rows)
        self.assertEqual(1, batch.stats.malformed_timestamp_rows)
        self.assertEqual(1, batch.stats.missing_volume_rows)
        self.assertEqual(1, batch.stats.unknown_site_rows)
        self.assertEqual(datetime(2026, 6, 1, 10, tzinfo=batch.observations[0].timestamp.tzinfo), batch.observations[0].timestamp)

    def test_unknown_site_and_missing_columns_raise_clear_errors(self) -> None:
        bad_path = Path(self.directory.name) / "bad.csv"
        bad_path.write_text("date,site\n2026-06-01,10001\n", encoding="utf-8")

        with self.assertRaisesRegex(VictoriaSchemaError, "missing required columns"):
            load_historical_observations(bad_path, self.sites_path)

    def test_heading_is_not_aggregated_across_directions_and_source_is_immutable(self) -> None:
        csv_path = self.write_csv(
            "directions.csv",
            [
                ["2026-06-01", "10:00", "10001", "North", "4bin", "90km/hr to < 95km/hr", "2"],
                ["2026-06-01", "10:00", "10001", "South", "4bin", "90km/hr to < 95km/hr", "3"],
            ],
        )
        before = csv_path.read_bytes()

        observations = load_historical_observations(csv_path, self.sites_path).observations

        self.assertEqual({2, 3}, {item.vehicle_count for item in observations})
        self.assertEqual(before, csv_path.read_bytes())


if __name__ == "__main__":
    unittest.main()