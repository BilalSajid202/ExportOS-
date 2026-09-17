"""
ExportOS — Application Configuration

Loads settings from environment variables / .env file using pydantic-settings.
Crashes early on misconfiguration so problems surface at startup, not at runtime.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exportos"

    # ── Security & Authentication ─────────────────────────────
    SECRET_KEY: str = "exportos-dev-super-secret-key-change-in-production-12345"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173"

    # ── Environment ───────────────────────────────────────────
    APP_ENV: str = "development"

    # ── App Info ──────────────────────────────────────────────
    APP_NAME: str = "ExportOS"
    APP_VERSION: str = "0.1.0"

    @property
    def effective_jwt_secret(self) -> str:
        """Use JWT_SECRET_KEY if explicitly provided, else fallback to SECRET_KEY."""
        return self.JWT_SECRET_KEY or self.SECRET_KEY

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. Call this instead of constructing Settings()
    directly so the .env file is read only once.
    """
    return Settings()
