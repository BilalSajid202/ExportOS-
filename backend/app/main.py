"""
Tradeloop — FastAPI Application Factory

Creates and configures the FastAPI application with:
  - CORS middleware
  - Structured logging
  - Lifespan handler (DB connection verification on startup)
  - Central API router mounted at /api
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import check_db_connection, engine
from app.api.router import api_router

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tradeloop")


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Startup: verify database connectivity
    - Shutdown: dispose the SQLAlchemy engine
    """
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Verify database on startup
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("Database connection verified ✓")
    else:
        logger.error("Database connection FAILED — app will start but /api/health will report unhealthy")

    yield

    # Shutdown: clean up engine
    await engine.dispose()
    logger.info("Database engine disposed. Goodbye.")


# ── App Factory ───────────────────────────────────────────────
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Export Operations Copilot — API",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
    )

    # ── CORS Middleware ───────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api")

    return app


# ── Application instance (used by uvicorn) ────────────────────
app = create_app()
