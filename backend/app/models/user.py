"""
ExportOS — User Model & Role Enumeration

Represents authenticated users in an Organisation.
Enforces Role-Based Access Control (RBAC) and tenant membership.
"""

import enum
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organisation import Organisation


class UserRole(str, enum.Enum):
    """
    Role definitions from ExportOS SRS.
    """
    ADMIN = "ADMIN"
    EXPORT_MANAGER = "EXPORT_MANAGER"
    DOCUMENTATION_OFFICER = "DOCUMENTATION_OFFICER"
    SALES = "SALES"
    ACCOUNTS = "ACCOUNTS"


class User(BaseModel):
    """
    User entity tied to a specific tenant Organisation.
    """

    __tablename__ = "users"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.SALES,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship(
        "Organisation",
        back_populates="users",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
