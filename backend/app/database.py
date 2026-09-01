import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

try:
    from app.config import settings
except ImportError:
    from .config import settings

logger = logging.getLogger("citytwin.database")

# Initialize database engine with connection pooling and pre-ping
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# Session factory for transactional scopes
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session for request lifecycle.
    Ensures connection is closed cleanly after response generation.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
