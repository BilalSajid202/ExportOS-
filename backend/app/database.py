"""
ExportOS — Database Engine & Session Management

Async SQLAlchemy engine using asyncpg.
Provides:
  - engine: the async engine instance
  - AsyncSessionLocal: session factory
  - get_db(): FastAPI dependency yielding a session per request
  - check_db_connection(): utility for health checks
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Async Engine ──────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)

# ── Session Factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── FastAPI Dependency ────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session per request.
    Commits on success, rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Health Check Utility ──────────────────────────────────────
async def check_db_connection() -> bool:
    """
    Attempt a simple query to verify the database is reachable.
    Returns True if connected, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
