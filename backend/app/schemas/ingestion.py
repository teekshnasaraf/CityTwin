from pydantic import BaseModel, Field


class CityIngestionRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=255, description="Name of the city to ingest from OpenStreetMap")
    country: str = Field(..., min_length=1, max_length=100, description="Name of the country where the city is located")


class CityIngestionResponse(BaseModel):
    status: str = Field(..., description="Ingestion operation status (e.g., success)")
    city: str = Field(..., description="Name of the ingested city")
    city_id: int = Field(..., description="Unique database ID for the city")
    roads: int = Field(..., description="Count of drivable road segments inserted")
    intersections: int = Field(..., description="Count of derived intersection points inserted")
    places: int = Field(..., description="Count of points of interest (POIs) inserted")
    ingestion_id: int = Field(..., description="Unique database ID of the audit ingestion log")
