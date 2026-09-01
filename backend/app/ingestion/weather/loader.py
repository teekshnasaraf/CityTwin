"""
Weather Data Loader and Quality Checker.
Validates meteorological parameters and stores observations in weather_state table.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.ingestion.weather.client import WeatherAPIClient
from app.models.state import WeatherState
from app.models.scenario import IngestionLog, DataQualityLog

logger = logging.getLogger("citytwin.ingestion.weather.loader")


class WeatherLoader:
    """Validates and persists weather state observations to database."""

    @classmethod
    def load_weather_data(cls, db: Session, city_id: int = 1, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Runs Weather ingestion ETL pipeline."""
        start_time = datetime.utcnow()
        obs = WeatherAPIClient.fetch_current_weather(api_key=api_key)

        # Validation checks
        temp_valid = -50.0 <= obs["temperature"] <= 60.0
        humidity_valid = 0.0 <= obs["humidity"] <= 100.0
        passed = temp_valid and humidity_valid

        try:
            ws = WeatherState(
                city_id=city_id,
                temperature=obs["temperature"],
                humidity=obs["humidity"],
                rainfall=obs["rainfall"],
                wind_speed=obs["wind_speed"],
                source=obs["source"],
                recorded_at=datetime.utcnow(),
            )
            db.add(ws)
            db.commit()
            db.refresh(ws)

            # Ingestion Log
            log_rec = IngestionLog(
                city_id=city_id,
                dataset_type="WEATHER",
                status="COMPLETED",
                records_processed=1,
                records_inserted=1,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )
            db.add(log_rec)
            db.commit()

            # Data Quality Log
            dq_rec = DataQualityLog(
                log_id=log_rec.log_id,
                dataset_type="WEATHER",
                check_name="weather_range_validation",
                passed=passed,
                details={"temp_valid": temp_valid, "humidity_valid": humidity_valid},
            )
            db.add(dq_rec)
            db.commit()
            weather_id = ws.weather_id
        except Exception as exc:
            logger.warning("DB insert for weather_state failed (%s)", str(exc))
            db.rollback()
            weather_id = 0

        return {
            "status": "COMPLETED",
            "city_id": city_id,
            "weather_id": weather_id,
            "observation": obs,
        }
