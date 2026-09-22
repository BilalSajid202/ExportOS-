"""
Tradeloop — Organisation Model

Represents a tenant (exporter organization/company).
All domain records (Users, Deals, InventoryItems, etc.) belong to an Organisation.
"""

from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Organisation(BaseModel):
    """
    Tenant Organisation entity.
    """

    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Pakistan", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organisation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Organisation id={self.id} name='{self.name}' slug='{self.slug}'>"
