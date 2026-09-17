"""
ExportOS — FastAPI Auth & Tenant Dependencies

Provides dependencies for:
  - Extracting and verifying JWT Bearer token
  - Resolving the current authenticated User and Organisation
  - Enforcing Role-Based Access Control (RBAC)
  - Ensuring tenant data isolation
"""

import uuid
from typing import Callable, List, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.database import get_db
from app.models.organisation import Organisation
from app.models.user import User, UserRole

# HTTP Bearer scheme (extracts `Authorization: Bearer <token>`)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts JWT from Authorization header, validates it, and fetches the active User
    from the database along with their Organisation.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        org_id_str: Optional[str] = payload.get("org_id")

        if not user_id_str or not org_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = uuid.UUID(user_id_str)
        org_id = uuid.UUID(org_id_str)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user from DB with organisation relationship loaded
    query = (
        select(User)
        .options(selectinload(User.organisation))
        .where(
            User.id == user_id,
            User.organisation_id == org_id,
            User.is_active.is_(True),
        )
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.organisation or not user.organisation.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation is inactive or deactivated",
        )

    return user


async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency ensuring the current user has the ADMIN role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required for this action",
        )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Factory dependency to enforce specific roles on endpoints.
    Example: Depends(require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER))
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


async def get_tenant_organisation(
    current_user: User = Depends(get_current_user),
) -> Organisation:
    """
    Returns the verified Organisation of the currently authenticated tenant user.
    """
    return current_user.organisation
