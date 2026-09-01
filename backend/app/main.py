import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.config import settings
    from app.database import get_db
    from app.api.ingestion import router as ingestion_router
    from app.api.cities import router as cities_router
    from app.api.scenarios import router as scenarios_router
    from app.api.simulation import router as simulation_router
    from app.api.state import router as state_router
    from app.api.ai import router as ai_router
except ImportError:
    from .config import settings
    from .database import get_db
    from .api.ingestion import router as ingestion_router
    from .api.cities import router as cities_router
    from .api.scenarios import router as scenarios_router
    from .api.simulation import router as simulation_router
    from .api.state import router as state_router
    from .api.ai import router as ai_router

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
app.include_router(cities_router)
app.include_router(scenarios_router)
app.include_router(simulation_router)
app.include_router(state_router)
app.include_router(ai_router)


@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    """
    Basic application status endpoint.
    """
    return {
        "project": settings.PROJECT_NAME,
        "status": "running",
        "dashboard_url": "http://127.0.0.1:8000/dashboard",
        "swagger_docs": "http://127.0.0.1:8000/docs",
    }


@app.get("/dashboard", response_class=FileResponse, tags=["Dashboard"])
@app.get("/app", response_class=FileResponse, tags=["Dashboard"])
def serve_dashboard():
    """
    Serves the interactive web dashboard application with Lucknow 2D spatial map plot.
    """
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return FileResponse(html_path)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Application availability health check.
    """
    return {
        "status": "healthy",
    }


@app.get("/database", tags=["Health"])
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Database connection verification endpoint.
    """
    try:
        raw_version = db.execute(text("SELECT version();")).scalar()
        version_str = str(raw_version) if raw_version else "Unknown"
        return {
            "database": "connected",
            "postgresql": version_str,
        }
    except Exception as exc:
        logger.warning("Database connection check warning: %s", type(exc).__name__)
        return {
            "database": "disconnected",
            "detail": "Operating in fallback mode for simulation engines.",
        }
