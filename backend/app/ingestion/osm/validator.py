import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger("citytwin.ingestion.osm.validator")


@dataclass
class ValidationReport:
    dataset_type: str
    total_records: int
    valid_records: int
    invalid_records: int
    passed: bool
    rejection_reasons: Dict[str, int] = field(default_factory=dict)


def validate_geometry(geom: Any) -> Tuple[bool, str]:
    """
    Validates that a geometry object is non-null, non-empty, and topologically valid.
    """
    if geom is None:
        return False, "geometry_is_null"
    if not isinstance(geom, BaseGeometry):
        return False, "geometry_invalid_type"
    if geom.is_empty:
        return False, "geometry_is_empty"
    if not geom.is_valid:
        return False, "geometry_is_invalid_topology"
    return True, ""


def validate_roads(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], ValidationReport]:
    """
    Validates road network records before database insertion.
    Filters out invalid records and produces a data quality audit report.
    """
    valid_records: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}

    for rec in records:
        geom = rec.get("geometry")
        is_valid, reason = validate_geometry(geom)
        if not is_valid:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        length_m = rec.get("length_m")
        if length_m is None or length_m < 0:
            reasons["invalid_length"] = reasons.get("invalid_length", 0) + 1
            continue

        valid_records.append(rec)

    total = len(records)
    valid_count = len(valid_records)
    invalid_count = total - valid_count
    passed = (valid_count > 0) if total > 0 else True

    report = ValidationReport(
        dataset_type="roads",
        total_records=total,
        valid_records=valid_count,
        invalid_records=invalid_count,
        passed=passed,
        rejection_reasons=reasons,
    )
    logger.info("Roads validation complete: %d valid, %d rejected out of %d", valid_count, invalid_count, total)
    return valid_records, report


def validate_intersections(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], ValidationReport]:
    """
    Validates intersection node records.
    """
    valid_records: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}

    for rec in records:
        geom = rec.get("geometry")
        is_valid, reason = validate_geometry(geom)
        if not is_valid:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        valid_records.append(rec)

    total = len(records)
    valid_count = len(valid_records)
    invalid_count = total - valid_count
    passed = (valid_count > 0) if total > 0 else True

    report = ValidationReport(
        dataset_type="intersections",
        total_records=total,
        valid_records=valid_count,
        invalid_records=invalid_count,
        passed=passed,
        rejection_reasons=reasons,
    )
    logger.info("Intersections validation complete: %d valid, %d rejected out of %d", valid_count, invalid_count, total)
    return valid_records, report


def validate_places(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], ValidationReport]:
    """
    Validates points of interest records.
    """
    valid_records: List[Dict[str, Any]] = []
    reasons: Dict[str, int] = {}

    for rec in records:
        geom = rec.get("geometry")
        is_valid, reason = validate_geometry(geom)
        if not is_valid:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        if not rec.get("place_type"):
            reasons["missing_place_type"] = reasons.get("missing_place_type", 0) + 1
            continue

        valid_records.append(rec)

    total = len(records)
    valid_count = len(valid_records)
    invalid_count = total - valid_count
    passed = True  # Places can be empty for small rural boundaries without invalidating ingestion

    report = ValidationReport(
        dataset_type="places",
        total_records=total,
        valid_records=valid_count,
        invalid_records=invalid_count,
        passed=passed,
        rejection_reasons=reasons,
    )
    logger.info("Places validation complete: %d valid, %d rejected out of %d", valid_count, invalid_count, total)
    return valid_records, report
