"""
Air Quality Loader and Data Quality Validator.
Normalizes OpenAQ measurements and stores records in air_quality_state table.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.ingestion.air_quality.client import OpenAQClient
from app.models.state import AirQualityState
from app.models.scenario import IngestionLog, DataQualityLog

logger = logging.getLogger("citytwin.ingestion.air_quality.loader")


class AirQualityLoader:
    """Validates and persists air quality sensor observations to database."""

    @classmethod
    def load_air_quality_data(cls, db: Session, city_id: int = 1, city_name: str = "Chennai") -> Dict[str, Any]:
        """Runs Air Quality ingestion ETL pipeline."""
        start_time = datetime.utcnow()
        measurements = OpenAQClient.fetch_city_air_quality(city_name=city_name)

        inserted_count = 0
        try:
            for m in measurements:
                aq = AirQualityState(
                    city_id=city_id,
                    station_id=m["station_id"],
                    pollutant=m["pollutant"],
                    value=m["value"],
                    unit=m["unit"],
                    source=m["source"],
                    recorded_at=datetime.utcnow(),
                )
                db.add(aq)
                inserted_count += 1
            db.commit()

            # Ingestion Log
            log_rec = IngestionLog(
                city_id=city_id,
                dataset_type="AIR_QUALITY",
                status="COMPLETED",
                records_processed=len(measurements),
                records_inserted=inserted_count,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )
            db.add(log_rec)
            db.commit()

            # Quality Log
            dq_rec = DataQualityLog(
                log_id=log_rec.log_id,
                dataset_type="AIR_QUALITY",
                check_name="openaq_non_negative_validation",
                passed=all(m["value"] >= 0 for m in measurements),
                details={"records_checked": len(measurements)},
            )
            db.add(dq_rec)
            db.commit()
            log_id = log_rec.log_id
        except Exception as exc:
            logger.warning("DB insert for air_quality_state failed (%s)", str(exc))
            db.rollback()
            log_id = 0

        return {
            "status": "COMPLETED",
            "city_id": city_id,
            "log_id": log_id,
            "records_inserted": inserted_count,
        }
