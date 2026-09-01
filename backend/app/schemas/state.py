"""
Pydantic Schemas for Dynamic State & Freshness Indicators.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TrafficStateResponse(BaseModel):
    city_id: int
    road_id: int
    vehicle_count: Optional[int] = None
    average_speed: Optional[float] = None
    congestion_level: Optional[float] = None
    source: Optional[str] = "Municipal Telemetry"
    data_type: str = "REALTIME"
    observed_at: datetime
    ingested_at: datetime
    freshness_seconds: int
    freshness_label: str

    model_config = ConfigDict(from_attributes=True)


class WeatherStateResponse(BaseModel):
    city_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    source: Optional[str] = "OpenAQ / Copernicus"
    data_type: str = "REALTIME"
    observed_at: datetime
    ingested_at: datetime
    freshness_seconds: int
    freshness_label: str

    model_config = ConfigDict(from_attributes=True)


class AirQualityStateResponse(BaseModel):
    city_id: int
    station_id: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    source: Optional[str] = "OpenAQ"
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
