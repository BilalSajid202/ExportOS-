"""
Tradeloop — Authentication API Routes

Endpoints:
  - POST /api/auth/register: Onboard company and create initial Admin user
  - POST /api/auth/login: Authenticate user and issue JWT access token
  - GET  /api/auth/me: Retrieve current authenticated user and organisation profile
"""

import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    OrganisationResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _slugify(text: str) -> str:
    """Generate a clean URL slug from company name."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "org"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new organisation and admin user",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Onboard a new exporting company.
    Atomically creates the Organisation entity and its primary ADMIN User account,
    then returns a JWT access token for immediate session establishment.
    """
    # Check if user email already exists
    existing_user_query = select(User).where(User.email == payload.email)
    existing_user_res = await db.execute(existing_user_query)
    if existing_user_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )

    # Generate unique slug for the organisation
    base_slug = _slugify(payload.company_name)
    slug = base_slug
    suffix_counter = 1

    while True:
        slug_check = await db.execute(select(Organisation).where(Organisation.slug == slug))
        if not slug_check.scalar_one_or_none():
            break
        slug = f"{base_slug}-{suffix_counter}"
        suffix_counter += 1

    # Create Organisation
    organisation = Organisation(
        name=payload.company_name,
        slug=slug,
        country=payload.country,
        default_currency=payload.default_currency.upper(),
        is_active=True,
    )
    db.add(organisation)
    await db.flush()  # Populates organisation.id

    # Create Admin User
    hashed_pwd = hash_password(payload.password)
    admin_user = User(
        organisation_id=organisation.id,
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    await db.refresh(organisation)

    # Generate Access Token
    token_payload = {
        "sub": str(admin_user.id),
        "org_id": str(organisation.id),
        "role": admin_user.role.value,
    }
    access_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(admin_user),
        organisation=OrganisationResponse.model_validate(organisation),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user with email and password",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Validates user credentials, checks tenant active status,
    and returns an access token with user and organisation profiles.
    """
    query = (
        select(User)
        .options(selectinload(User.organisation))
        .where(User.email == payload.email)
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact your organisation admin.",
        )

    if not user.organisation or not user.organisation.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation account is deactivated.",
        )

    token_payload = {
        "sub": str(user.id),
        "org_id": str(user.organisation_id),
        "role": user.role.value,
    }
    access_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(user.organisation),
    )


@router.get(
    "/me",
    summary="Get current authenticated user and organisation profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns full details of the currently authenticated user and their active tenant organisation.
    """
    return {
        "user": UserResponse.model_validate(current_user),
        "organisation": OrganisationResponse.model_validate(current_user.organisation),
    }
