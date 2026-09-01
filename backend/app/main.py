import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.config import settings
    from app.database import get_db
    from app.api.ingestion import router as ingestion_router
except ImportError:
    from .config import settings
    from .database import get_db
    from .api.ingestion import router as ingestion_router

# Configure logger
logger = logging.getLogger("citytwin.api")

# Initialize FastAPI application
app = FastAPI(
    title="CITYTWIN API",
    description="AI-Powered Urban Digital Twin for Scenario-Based Decision Intelligence",
    version="0.1.0",
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(ingestion_router)


@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    """
    Basic application status endpoint.
    """
    return {
        "project": settings.PROJECT_NAME,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Application availability health check.
    Independent of external services or database connectivity.
    """
    return {
        "status": "healthy",
    }


@app.get("/database", tags=["Health"])
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Database connection verification endpoint.
    Executes a lightweight query to verify connectivity and retrieve version info securely.
    """
    try:
        raw_version = db.execute(text("SELECT version();")).scalar()
        version_str = str(raw_version) if raw_version else "Unknown"
        return {
            "database": "connected",
            "postgresql": version_str,
        }
    except Exception as exc:
        logger.error("Database connection check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "database": "disconnected",
                "detail": "Could not establish connection to the database.",
            },
        )
