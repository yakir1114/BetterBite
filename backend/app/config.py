"""Application settings, loaded from environment variables only (12-factor).

Mirrors the keys documented in the repo-root ``.env.example``. Nothing here
should ever hold a default secret — secrets come from the environment.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    env: str = "local"  # local | staging | production
    api_base_path: str = "/api/v1"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/betterbite"
    )

    # --- Firebase (Auth / Storage) ---
    firebase_project_id: str | None = None
    google_application_credentials: str | None = None
    firebase_storage_bucket: str | None = None

    # --- AI providers (server-side only; never shipped to the client) ---
    ai_vision_provider: str | None = None
    ai_vision_api_key: str | None = None
    ai_text_provider: str | None = None
    ai_text_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (one instance per process)."""
    return Settings()
