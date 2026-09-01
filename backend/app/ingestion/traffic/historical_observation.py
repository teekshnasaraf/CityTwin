"""Historical traffic observations normalized from Victoria telemetry files."""

from dataclasses import dataclass, field
from datetime import datetime
import csv
from collections.abc import Iterable, Iterator, Mapping, Sequence
from io import TextIOWrapper
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo


VICTORIA_COLUMNS = frozenset({"date", "time_bin", "site", "heading", "vehicle_class", "speed_bin", "volume"})
DEFAULT_TIMEZONE = "Australia/Melbourne"
VICTORIA_SOURCE = "victoria_telemetry"


class VictoriaSchemaError(ValueError):
    """Raised when a source file does not have the expected Victoria schema."""


@dataclass(frozen=True)
class TelemetrySite:
    site_id: str
    description: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class HistoricalTrafficObservation:
    """Aggregated sensor observation, intentionally distinct from a road state."""

    timestamp: datetime
    site_id: str
    heading: str
    vehicle_count: int
    latitude: float
    longitude: float
    source: str = VICTORIA_SOURCE
    data_type: str = "HISTORICAL"
    vehicle_class_counts: Mapping[str, int] = field(default_factory=dict)
    speed_bin_counts: Mapping[str, int] = field(default_factory=dict)
    site_description: str = ""
    source_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        if not self.site_id:
            raise ValueError("site_id must not be empty")
        if not self.heading:
            raise ValueError("heading must not be empty")
        if self.vehicle_count < 0:
            raise ValueError("vehicle_count must not be negative")
        if self.data_type != "HISTORICAL":
            raise ValueError("Victoria observations must use data_type HISTORICAL")
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("site coordinates are outside valid ranges")

    @property
    def sensor_identifier(self) -> str:
        """Return an explicit sensor identity; this is not an OSM road ID."""
        normalized_heading = "_".join(self.heading.lower().split())
        return f"vic_sensor_{self.site_id}_{normalized_heading}"


@dataclass
class HistoricalObservationStats:
    csv_members_processed: int = 0
    raw_rows_encountered: int = 0
    valid_rows: int = 0
    skipped_rows: int = 0
    malformed_timestamp_rows: int = 0
    missing_volume_rows: int = 0
    invalid_volume_rows: int = 0
    missing_site_rows: int = 0
    missing_heading_rows: int = 0
    missing_vehicle_class_rows: int = 0
    missing_speed_bin_rows: int = 0
    unknown_site_rows: int = 0
    invalid_heading_rows: int = 0


@dataclass(frozen=True)
class HistoricalObservationBatch:
    observations: tuple[HistoricalTrafficObservation, ...]
    stats: HistoricalObservationStats


@dataclass
class _Aggregate:
    timestamp: datetime
    site: TelemetrySite
    heading: str
    vehicle_count: int = 0
    vehicle_class_counts: dict[str, int] = field(default_factory=dict)
    speed_bin_counts: dict[str, int] = field(default_factory=dict)
    source_files: set[str] = field(default_factory=set)


def load_telemetry_sites(path: str | Path) -> dict[str, TelemetrySite]:
    """Load and validate Victoria site metadata without changing the source."""
    sites: dict[str, TelemetrySite] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        expected = {"site", "site_description", "latitude", "longitude"}
        _validate_columns(reader.fieldnames, expected, str(path))
        for row_number, row in enumerate(reader, start=2):
            try:
                site_id = _required(row, "site", row_number)
                sites[site_id] = TelemetrySite(
                    site_id=site_id,
                    description=_required(row, "site_description", row_number),
                    latitude=float(_required(row, "latitude", row_number)),
                    longitude=float(_required(row, "longitude", row_number)),
                )
            except (TypeError, ValueError) as error:
                raise VictoriaSchemaError(f"invalid telemetry site row {row_number}: {error}") from error
    return sites


def load_historical_observations(
    inputs: str | Path | Iterable[str | Path],
    sites_path: str | Path,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> HistoricalObservationBatch:
    """Read CSV/ZIP inputs and aggregate rows to site-heading-timestamp observations."""
    timezone = ZoneInfo(timezone_name)
    sites = load_telemetry_sites(sites_path)
    aggregates: dict[tuple[str, str, datetime], _Aggregate] = {}
    stats = HistoricalObservationStats()
    for source_name, handle in _open_csv_sources(_as_paths(inputs)):
        stats.csv_members_processed += 1
        with handle:
            reader = csv.DictReader(handle)
            _validate_columns(reader.fieldnames, VICTORIA_COLUMNS, source_name)
            for row_number, row in enumerate(reader, start=2):
                stats.raw_rows_encountered += 1
                try:
                    timestamp = _parse_timestamp(row, row_number, timezone)
                    site_id = _required(row, "site", row_number)
                    heading = _required(row, "heading", row_number)
                    vehicle_class = _required(row, "vehicle_class", row_number)
                    speed_bin = _required(row, "speed_bin", row_number)
                    volume = _parse_volume(row, row_number)
                    if site_id not in sites:
                        raise _RowSkip(f"unknown site {site_id!r}", "unknown_site_rows")
                    key = (site_id, heading, timestamp)
                    aggregate = aggregates.setdefault(key, _Aggregate(timestamp, sites[site_id], heading))
                    aggregate.vehicle_count += volume
                    aggregate.vehicle_class_counts[vehicle_class] = aggregate.vehicle_class_counts.get(vehicle_class, 0) + volume
                    aggregate.speed_bin_counts[speed_bin] = aggregate.speed_bin_counts.get(speed_bin, 0) + volume
                    aggregate.source_files.add(source_name)
                    stats.valid_rows += 1
                except _RowSkip as skipped:
                    stats.skipped_rows += 1
                    setattr(stats, skipped.stat_name, getattr(stats, skipped.stat_name) + 1)
    observations = tuple(
        HistoricalTrafficObservation(
            timestamp=aggregate.timestamp,
            site_id=aggregate.site.site_id,
            heading=aggregate.heading,
            vehicle_count=aggregate.vehicle_count,
            latitude=aggregate.site.latitude,
            longitude=aggregate.site.longitude,
            vehicle_class_counts=dict(sorted(aggregate.vehicle_class_counts.items())),
            speed_bin_counts=dict(sorted(aggregate.speed_bin_counts.items())),
            site_description=aggregate.site.description,
            source_files=tuple(sorted(aggregate.source_files)),
        )
        for aggregate in sorted(aggregates.values(), key=lambda item: (item.timestamp, item.site.site_id, item.heading))
    )
    return HistoricalObservationBatch(observations, stats)


def _as_paths(inputs: str | Path | Iterable[str | Path]) -> list[Path]:
    if isinstance(inputs, (str, Path)):
        return [Path(inputs)]
    return [Path(input_path) for input_path in inputs]


def _open_csv_sources(paths: Sequence[Path]) -> Iterator[tuple[str, TextIOWrapper]]:
    for path in paths:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                members = [member for member in archive.namelist() if member.lower().endswith(".csv")]
            for member in sorted(members):
                member_archive = zipfile.ZipFile(path)
                raw_handle = member_archive.open(member)
                text_handle = TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="")
                yield f"{path}!{member}", _ArchiveTextHandle(text_handle, member_archive)
        elif path.suffix.lower() == ".csv":
            yield str(path), path.open(newline="", encoding="utf-8-sig")
        else:
            raise VictoriaSchemaError(f"unsupported traffic input type: {path}")


class _ArchiveTextHandle(TextIOWrapper):
    def __init__(self, handle: TextIOWrapper, archive: zipfile.ZipFile) -> None:
        self._archive = archive
        super().__init__(handle.buffer, encoding="utf-8-sig", newline="")

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._archive.close()


def _validate_columns(fieldnames: list[str] | None, expected: set[str] | frozenset[str], source: str) -> None:
    actual = set(fieldnames or ())
    missing = expected - actual
    if missing:
        raise VictoriaSchemaError(f"{source} is missing required columns: {sorted(missing)}")


def _required(row: Mapping[str, str | None], name: str, row_number: int) -> str:
    value = (row.get(name) or "").strip()
    if not value:
        raise _RowSkip(f"missing {name} at row {row_number}", f"missing_{name}_rows")
    return value


def _parse_timestamp(row: Mapping[str, str | None], row_number: int, timezone: ZoneInfo) -> datetime:
    date_value = (row.get("date") or "").strip()
    time_value = (row.get("time_bin") or "").strip()
    try:
        return datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone)
    except ValueError as error:
        raise _RowSkip(f"invalid timestamp at row {row_number}: {error}", "malformed_timestamp_rows") from error


def _parse_volume(row: Mapping[str, str | None], row_number: int) -> int:
    value = (row.get("volume") or "").strip()
    if not value:
        raise _RowSkip(f"missing volume at row {row_number}", "missing_volume_rows")
    try:
        volume = int(value)
    except ValueError as error:
        raise _RowSkip(f"invalid volume at row {row_number}", "invalid_volume_rows") from error
    if volume < 0:
        raise _RowSkip(f"negative volume at row {row_number}", "invalid_volume_rows")
    return volume


class _RowSkip(ValueError):
    def __init__(self, message: str, stat_name: str) -> None:
        super().__init__(message)
        self.stat_name = stat_name