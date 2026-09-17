"""
Pydantic response schema for the health endpoint.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for GET /api/health."""

    status: str
    database: str
    version: str
    environment: str
