"""
ExportOS — Application Configuration

Loads settings from environment variables / .env file using pydantic-settings.
Crashes early on misconfiguration so problems surface at startup, not at runtime.
"""

from functools import lru_cache
from typing import List
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

    # ── AI / Hugging Face Qwen Configuration ──────────────────
    # Multiple comma-separated keys for auto-rotation on rate limits: hf_key1,hf_key2,hf_key3
    HF_API_KEYS: str = ""
    HF_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"

    # ── Storage ───────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"

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
    def hf_keys_list(self) -> List[str]:
        """Parse comma-separated Hugging Face API keys."""
        if not self.HF_API_KEYS:
            return []
        return [k.strip() for k in self.HF_API_KEYS.split(",") if k.strip()]

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
