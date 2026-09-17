"""
ExportOS — Users API Routes

Provides dedicated endpoints for user management, profiles, and team operations:
  - GET    /api/users/me          - Retrieve current authenticated user's profile
  - PUT    /api/users/me          - Update current user's profile
  - GET    /api/users             - List all users in caller's organisation (tenant-isolated)
  - POST   /api/users             - Invite/create new team member (Admin only)
  - GET    /api/users/{user_id}   - Retrieve a specific user in organisation
  - PUT    /api/users/{user_id}   - Update user role or active status (Admin only)
  - DELETE /api/users/{user_id}   - Deactivate user (Admin only)
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_active_admin, get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import CreateUserRequest, EmailType, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


class UpdateProfileRequest(BaseModel):
    """Payload for updating own profile."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)


class UpdateUserAdminRequest(BaseModel):
    """Payload for admin updating another user's role or status."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns profile information for the currently logged-in user."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Updates the full name or profile fields of the currently logged-in user."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List all users in current organisation",
)
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """
    Lists all members within the caller's tenant organisation.
    Enforces strict tenant isolation.
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
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user in organisation (Admin only)",
)
async def create_user(
    payload: CreateUserRequest,
    admin_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Creates a new user assigned to the caller's organisation.
    Restricted to tenant Admins.
    """
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


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Retrieve details of a user belonging to the same organisation."""
    query = select(User).where(
        User.id == user_id,
        User.organisation_id == current_user.organisation_id,
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user role or status (Admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UpdateUserAdminRequest,
    admin_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Updates a user's role or active status. Restricted to Admins."""
    query = select(User).where(
        User.id == user_id,
        User.organisation_id == admin_user.organisation_id,
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        # Prevent self-deactivation if last admin
        if user.id == admin_user.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own admin account",
            )
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate/delete user (Admin only)",
)
async def delete_user(
    user_id: uuid.UUID,
    admin_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivates a user in the organisation. Restricted to Admins."""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account",
        )

    query = select(User).where(
        User.id == user_id,
        User.organisation_id == admin_user.organisation_id,
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organisation",
        )

    await db.delete(user)
    await db.commit()
    return None
