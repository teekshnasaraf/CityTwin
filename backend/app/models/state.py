"""
Dynamic City State SQLAlchemy ORM definitions.
Represents time-series traffic, weather, and air quality observations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database import Base
except ImportError:
    from ..database import Base


class TrafficState(Base):
    """Stores time-series traffic observations and dynamic edge state."""
    __tablename__ = "traffic_state"

    traffic_id = Column(BigInteger, primary_key=True, index=True)
    road_id = Column(BigInteger, ForeignKey("roads.road_id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_count = Column(Integer, nullable=True)
    average_speed = Column(Float, nullable=True)
    congestion_level = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    road = relationship("Road", back_populates="traffic_states")


class WeatherState(Base):
    """Stores time-series meteorological observations across city areas."""
    __tablename__ = "weather_state"

    weather_id = Column(BigInteger, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)


class AirQualityState(Base):
    """Stores time-series air quality measurements across stations."""
    __tablename__ = "air_quality_state"

    air_quality_id = Column(BigInteger, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    station_id = Column(String(100), nullable=True)
    pollutant = Column(String(50), nullable=True)
    value = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
