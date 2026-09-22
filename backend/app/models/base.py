"""
Tradeloop — SQLAlchemy Base & Common Model Mixin

Every domain entity (Organisation, User, Deal, InventoryItem, etc.)
inherits from BaseModel to get:
  - UUID primary key
  - created_at / updated_at timestamps
  - Consistent table naming
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all Tradeloop models."""
    pass


class BaseModel(Base):
    """
    Abstract base providing common columns for every table.

    Columns:
        id          — UUID primary key, generated server-side
        created_at  — Timestamp set on INSERT
        updated_at  — Timestamp updated on every UPDATE
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
