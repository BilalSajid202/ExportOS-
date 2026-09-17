"""
ExportOS — Health Check Endpoint

GET /api/health
Returns the application and database status.
"""

import logging

from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_connection
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Application health check.

    Verifies the database connection and returns system status.
    Used by the frontend dashboard and monitoring tools.
    """
    settings = get_settings()
    db_connected = await check_db_connection()

    status = "healthy" if db_connected else "unhealthy"
    db_status = "connected" if db_connected else "disconnected"

    if not db_connected:
        logger.warning("Health check: database is unreachable")

    return HealthResponse(
        status=status,
        database=db_status,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
