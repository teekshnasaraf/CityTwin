"""
Pydantic Schemas for Cities, Roads, Intersections, and Places.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CityBase(BaseModel):
    name: str
    country: str
    state: Optional[str] = None
    latitude: Optional[float] = 13.0827
    longitude: Optional[float] = 80.2707


class CityCreate(CityBase):
    pass


class CityResponse(CityBase):
    city_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RoadResponse(BaseModel):
    road_id: int
    city_id: int
    osm_id: Optional[int] = None
    name: Optional[str] = None
    road_type: Optional[str] = None
    length_m: Optional[float] = None
    speed_limit: Optional[float] = None
    lanes: Optional[int] = None
    capacity: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class IntersectionResponse(BaseModel):
    intersection_id: int
    city_id: int
    osm_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PlaceResponse(BaseModel):
    place_id: int
    city_id: int
    name: Optional[str] = None
    place_type: str

    model_config = ConfigDict(from_attributes=True)
