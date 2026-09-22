"""
Tradeloop — Organisation & Team Management API Routes

Enforces tenant isolation:
  - All queries filter strictly by `current_user.organisation_id`
  - Administrative mutations require `ADMIN` role
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_admin, get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.organisation import Organisation
from app.models.user import User
from app.schemas.auth import (
    CreateUserRequest,
    OrganisationResponse,
    OrganisationUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/organisation", tags=["Organisation & Team"])


@router.get(
    "/me",
    response_model=OrganisationResponse,
    summary="Get current tenant organisation settings",
)
async def get_my_organisation(
    current_user: User = Depends(get_current_user),
) -> OrganisationResponse:
    """Returns profile and settings of the current user's organisation."""
    return OrganisationResponse.model_validate(current_user.organisation)


@router.put(
    "/me",
    response_model=OrganisationResponse,
    summary="Update current organisation settings (Admin only)",
)
async def update_my_organisation(
    payload: OrganisationUpdateRequest,
    admin_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    """Updates organisation profile. Restricted to tenant ADMINs."""
    org: Organisation = admin_user.organisation

    if payload.name is not None:
        org.name = payload.name
    if payload.country is not None:
        org.country = payload.country
    if payload.default_currency is not None:
        org.default_currency = payload.default_currency.upper()

    await db.commit()
    await db.refresh(org)
    return OrganisationResponse.model_validate(org)


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List team members in the current organisation",
)
async def list_organisation_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """
    Lists all members within the caller's organisation.
    Enforces strict tenant isolation — never returns users from another organisation.
    """
    query = (
        select(User)
        .where(User.organisation_id == current_user.organisation_id)
        .order_by(User.created_at.asc())
    )
    result = await db.execute(query)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new team member to organisation (Admin only)",
)
async def create_organisation_user(
    payload: CreateUserRequest,
    admin_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Creates a new user assigned to the caller's organisation with the specified role.
    Restricted to tenant ADMINs.
    """
    # Check if email is already taken globally
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    new_user = User(
        organisation_id=admin_user.organisation_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse.model_validate(new_user)
