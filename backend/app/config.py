"""Environment-based configuration.

Every setting can be supplied as an environment variable (or in a local .env
file). Names are case-insensitive, e.g. DATABASE_URL, ADZUNA_APP_ID.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_SEARCH_TERMS = [
    "data analyst",
    "marketing analyst",
    "business analyst",
    "analytics engineer",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./market_tracker.db"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "us"
    adzuna_base_url: str = "https://api.adzuna.com/v1/api/jobs"

    search_terms: Annotated[list[str], NoDecode] = DEFAULT_SEARCH_TERMS
    # Comma-separated list of allowed frontend origins, or "*".
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("search_terms", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        # Neon / Supabase / Render hand out postgres:// or postgresql:// URLs;
        # SQLAlchemy needs the driver named explicitly to use psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
