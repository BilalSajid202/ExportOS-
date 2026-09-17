"""
ExportOS — Minimal Deal Model (Phase 3 connection)

Phase 3 needs a lightweight deal so employees can:
  1. Manually create a deal with product + quantity
  2. See inventory availability immediately
  3. Optionally reserve stock

Full deal state machine expands in Phase 4.
"""

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.product import Product
    from app.models.user import User
    from app.models.inventory import InventoryReservation


class DealState(str, enum.Enum):
    INQUIRY = "INQUIRY"
    QUOTED = "QUOTED"
    CONFIRMED = "CONFIRMED"
    IN_PRODUCTION = "IN_PRODUCTION"
    DOCS_READY = "DOCS_READY"
    SHIPPED = "SHIPPED"
    PAID = "PAID"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Deal(BaseModel):
    """Central commercial opportunity — minimal fields for Phase 3."""

    __tablename__ = "deals"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[DealState] = mapped_column(
        Enum(DealState, name="deal_state", native_enum=False),
        default=DealState.INQUIRY,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    creator: Mapped[Optional["User"]] = relationship("User", lazy="joined")
    line_items: Mapped[List["DealLineItem"]] = relationship(
        "DealLineItem",
        back_populates="deal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reservations: Mapped[List["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="deal",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Deal id={self.id} ref='{self.reference}' state={self.state}>"


class DealLineItem(BaseModel):
    """One product quantity on a deal."""

    __tablename__ = "deal_line_items"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    deal: Mapped["Deal"] = relationship("Deal", back_populates="line_items", lazy="joined")
    product: Mapped["Product"] = relationship("Product", lazy="joined")

    def __repr__(self) -> str:
        return f"<DealLineItem id={self.id} product={self.product_id} qty={self.quantity}>"
