"""
Base City Model SQLAlchemy ORM definitions.
Represents geographic baseline data for cities, roads, intersections, and places.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

try:
    from app.database import Base
except ImportError:
    from ..database import Base


class City(Base):
    """Stores city metadata and spatial boundaries."""
    __tablename__ = "cities"

    city_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    roads = relationship("Road", back_populates="city", cascade="all, delete-orphan")
    intersections = relationship("Intersection", back_populates="city", cascade="all, delete-orphan")
    places = relationship("Place", back_populates="city", cascade="all, delete-orphan")


class Intersection(Base):
    """Stores road intersections / graph nodes extracted from street network data."""
    __tablename__ = "intersections"

    intersection_id = Column(BigInteger, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    osm_id = Column(BigInteger, nullable=True, index=True)
    geometry = Column(Geometry("POINT", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    city = relationship("City", back_populates="intersections")


class Road(Base):
    """Stores street network segments / graph edges with physical and operational attributes."""
    __tablename__ = "roads"

    road_id = Column(BigInteger, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    osm_id = Column(BigInteger, nullable=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    road_type = Column(String(50), nullable=True)
    length_m = Column(Float, nullable=True)
    speed_limit = Column(Float, nullable=True)
    lanes = Column(Integer, nullable=True)
    capacity = Column(Float, nullable=True)
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    city = relationship("City", back_populates="roads")
    traffic_states = relationship("TrafficState", back_populates="road", cascade="all, delete-orphan")


class Place(Base):
    """Stores POIs, critical infrastructure (hospitals, fire/police stations, schools)."""
    __tablename__ = "places"

    place_id = Column(BigInteger, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    osm_id = Column(BigInteger, nullable=True, index=True)
    name = Column(String(255), nullable=True)
    place_type = Column(String(100), nullable=False, index=True)
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    city = relationship("City", back_populates="places")
