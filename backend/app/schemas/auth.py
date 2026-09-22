"""
Tradeloop — Authentication & Organisation Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.user import UserRole

# RFC 5322-compliant simple email regex constraint
EmailType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    ),
]


# ── Organisation Schemas ──────────────────────────────────────────────

class OrganisationResponse(BaseModel):
    """Organisation representation returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    country: str
    default_currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganisationUpdateRequest(BaseModel):
    """Payload to update organisation settings."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    default_currency: Optional[str] = Field(None, min_length=3, max_length=3)


# ── User Schemas ──────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """User representation returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateUserRequest(BaseModel):
    """Admin request to invite/create a new team member in their organisation."""
    email: EmailType
    password: str = Field(..., min_length=6, description="Initial password")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = Field(default=UserRole.SALES)


# ── Auth & Onboarding Schemas ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Company registration payload creating both Organisation and initial Admin user."""
    company_name: str = Field(..., min_length=2, max_length=255, description="Exporter company name")
    country: str = Field(default="Pakistan", max_length=100)
    default_currency: str = Field(default="USD", min_length=3, max_length=3)
    full_name: str = Field(..., min_length=2, max_length=255, description="Admin full name")
    email: EmailType
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")


class LoginRequest(BaseModel):
    """Login payload."""
    email: EmailType
    password: str


class TokenResponse(BaseModel):
    """Auth response containing JWT and entity info."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organisation: OrganisationResponse
