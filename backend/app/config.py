"""
ExportOS — Application Configuration

Loads settings from environment variables / .env file using pydantic-settings.
Crashes early on misconfiguration so problems surface at startup, not at runtime.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exportos"

    # ── Security & Authentication ─────────────────────────────
    SECRET_KEY: str = "exportos-dev-super-secret-key-change-in-production-12345"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── AI / Hugging Face Qwen Configuration ──────────────────
    HF_MODEL: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    HF_API_URL: str = "https://router.huggingface.co/v1/chat/completions"
    HF_API_KEYS: str = ""
    HF_API_KEY_1: Optional[str] = None
    HF_API_KEY_2: Optional[str] = None
    HF_API_KEY_3: Optional[str] = None
    HF_API_KEY_4: Optional[str] = None
    HF_API_KEY_5: Optional[str] = None

    # ── Vector Database (Qdrant) & Knowledge Docs ────────────
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PATH: str = "qdrant_storage"
    QDRANT_COLLECTION_NAME: str = "exportos_copilot"
    DOCS_DATA_DIR: str = "data/docs"

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
        """Aggregate Hugging Face API keys from individual numbered keys or comma-separated list."""
        keys: List[str] = []
        for individual in [
            self.HF_API_KEY_1,
            self.HF_API_KEY_2,
            self.HF_API_KEY_3,
            self.HF_API_KEY_4,
            self.HF_API_KEY_5,
        ]:
            if individual and individual.strip():
                keys.append(individual.strip())

        if self.HF_API_KEYS:
            for k in self.HF_API_KEYS.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        return keys

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
