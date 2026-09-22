"""
Tradeloop — Inventory Models

Deterministic stock tracking:
  - InventoryItem: current / reserved quantities per product
  - InventoryTransaction: append-only stock movement log
  - InventoryReservation: holds against deals

available_quantity = current_quantity - reserved_quantity  (computed, never stored)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.product import Product
    from app.models.deal import Deal
    from app.models.user import User


class InventoryTransactionType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    ADJUSTMENT = "ADJUSTMENT"
    RESERVATION = "RESERVATION"
    RELEASE = "RELEASE"
    SHIPMENT = "SHIPMENT"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONSUMED = "CONSUMED"
    CANCELLED = "CANCELLED"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class InventoryItem(BaseModel):
    """
    Stock record for a single product within an organisation.
    One inventory row per product (enforced by unique product_id).
    """

    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_inventory_items_product_id"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0"),
        nullable=False,
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0"),
        nullable=False,
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0"),
        nullable=False,
    )
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="PCS", nullable=False)

    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="inventory_item",
        lazy="joined",
    )
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction",
        back_populates="inventory_item",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="inventory_item",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    @property
    def available_quantity(self) -> Decimal:
        """Deterministic availability: current − reserved."""
        return self.current_quantity - self.reserved_quantity

    def __repr__(self) -> str:
        return (
            f"<InventoryItem id={self.id} sku='{self.sku}' "
            f"current={self.current_quantity} reserved={self.reserved_quantity}>"
        )


class InventoryTransaction(BaseModel):
    """Append-only log of stock quantity changes."""

    __tablename__ = "inventory_transactions"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[InventoryTransactionType] = mapped_column(
        Enum(InventoryTransactionType, name="inventory_transaction_type", native_enum=False),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    inventory_item: Mapped["InventoryItem"] = relationship(
        "InventoryItem",
        back_populates="transactions",
        lazy="joined",
    )
    creator: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<InventoryTransaction id={self.id} type={self.transaction_type} "
            f"qty={self.quantity}>"
        )


class InventoryReservation(BaseModel):
    """Stock hold against a deal line / product."""

    __tablename__ = "inventory_reservations"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)

    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status", native_enum=False),
        default=ReservationStatus.ACTIVE,
        nullable=False,
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    inventory_item: Mapped["InventoryItem"] = relationship(
        "InventoryItem",
        back_populates="reservations",
        lazy="joined",
    )
    deal: Mapped[Optional["Deal"]] = relationship(
        "Deal",
        back_populates="reservations",
        lazy="joined",
    )
    creator: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<InventoryReservation id={self.id} qty={self.quantity} "
            f"status={self.status}>"
        )
