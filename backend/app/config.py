"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every field can be overridden with an env var of the same name."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MediSlot API"
    # Injected by CI/Helm as the Git commit SHA so every running pod is traceable to source.
    app_version: str = "dev"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://medislot:medislot@localhost:5432/medislot"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
