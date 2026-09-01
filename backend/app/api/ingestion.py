import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from app.database import get_db
    from app.schemas.ingestion import CityIngestionRequest, CityIngestionResponse
    from app.ingestion.osm import (
        ingest_osm_city,
        CityNotFoundError,
        OSMDownloadError,
    )
except ImportError:
    from backend.app.database import get_db
    from backend.app.schemas.ingestion import CityIngestionRequest, CityIngestionResponse
    from backend.app.ingestion.osm import (
        ingest_osm_city,
        CityNotFoundError,
        OSMDownloadError,
    )

logger = logging.getLogger("citytwin.api.ingestion")

router = APIRouter(prefix="/api/v1/ingestion", tags=["Ingestion"])


@router.post(
    "/osm/city",
    response_model=CityIngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest city geographic baseline from OpenStreetMap",
    description="Resolves city boundaries, downloads drivable road networks and POIs, validates geometries, and loads them into PostgreSQL/PostGIS with data provenance records.",
)
def ingest_city_from_osm(
    payload: CityIngestionRequest,
    db: Session = Depends(get_db),
) -> CityIngestionResponse:
    """
    Triggers the end-to-end OpenStreetMap ingestion pipeline for a given city and country.
    """
    clean_city = payload.city.strip()
    clean_country = payload.country.strip()

    if not clean_city or not clean_country:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="City and country names must be non-empty strings.",
        )

    logger.info("Received OSM city ingestion request: city='%s', country='%s'", clean_city, clean_country)

    try:
        result = ingest_osm_city(
            city=clean_city,
            country=clean_country,
            db=db,
        )
        return CityIngestionResponse(**result)

    except CityNotFoundError as err:
        logger.warning("City resolution failed for '%s, %s': %s", clean_city, clean_country, str(err))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{clean_city}, {clean_country}' could not be resolved by OpenStreetMap/Nominatim.",
        )

    except OSMDownloadError as err:
        logger.error("OSM network download failed for '%s, %s': %s", clean_city, clean_country, str(err))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to retrieve data from OpenStreetMap service: {str(err)}",
        )

    except Exception as exc:
        logger.error("Unexpected error during OSM ingestion for '%s, %s': %s", clean_city, clean_country, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during the city ingestion pipeline.",
        )
