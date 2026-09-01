import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Load .env file if present in workspace root or backend directory
env_file_root = ROOT_DIR / ".env"
env_file_backend = BACKEND_DIR / ".env"

if env_file_root.exists():
    load_dotenv(dotenv_path=env_file_root)
elif env_file_backend.exists():
    load_dotenv(dotenv_path=env_file_backend)
else:
    load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "CITYTWIN"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:@localhost:5432/citytwin",
        description="PostgreSQL connection string with psycopg driver",
    )
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=(str(env_file_root), str(env_file_backend), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
