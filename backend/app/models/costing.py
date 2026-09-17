"""
ExportOS — Costing & Quotation Models (Phase 8)

Entities:
- CostComponent: granular cost items (packaging, freight, insurance, etc.) associated with a deal.
- DealQuote: calculated quote record with Incoterm, subtotal, margin, and approval status.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.user import User


class Incoterm(str, enum.Enum):
    EXW = "EXW"  # Ex Works
    FCA = "FCA"  # Free Carrier
    FOB = "FOB"  # Free on Board
    CFR = "CFR"  # Cost and Freight
    CIF = "CIF"  # Cost, Insurance and Freight
    CPT = "CPT"  # Carriage Paid To
    CIP = "CIP"  # Carriage and Insurance Paid to
    DAP = "DAP"  # Delivered at Place
    DDP = "DDP"  # Delivered Duty Paid


class CostComponentType(str, enum.Enum):
    PRODUCT_BASE = "PRODUCT_BASE"
    PACKAGING = "PACKAGING"
    INLAND_FREIGHT = "INLAND_FREIGHT"
    PORT_HANDLING = "PORT_HANDLING"
    EXPORT_CLEARANCE = "EXPORT_CLEARANCE"
    OCEAN_FREIGHT = "OCEAN_FREIGHT"
    AIR_FREIGHT = "AIR_FREIGHT"
    INSURANCE = "INSURANCE"
    IMPORT_DUTIES = "IMPORT_DUTIES"
    OTHER = "OTHER"


class QuoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class CostComponent(BaseModel):
    """Line-item cost breakdown component for a deal."""

    __tablename__ = "cost_components"

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

    cost_type: Mapped[CostComponentType] = mapped_column(
        Enum(CostComponentType, name="cost_component_type", native_enum=False),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    deal: Mapped["Deal"] = relationship("Deal", lazy="joined")

    def __repr__(self) -> str:
        return f"<CostComponent id={self.id} type={self.cost_type} amount={self.amount} {self.currency}>"


class DealQuote(BaseModel):
    """Calculated commercial quotation for a deal under a specific Incoterm."""

    __tablename__ = "deal_quotes"

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

    incoterm: Mapped[Incoterm] = mapped_column(
        Enum(Incoterm, name="incoterm", native_enum=False),
        nullable=False,
    )
    incoterm_place: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Financials (Deterministic Decimal values)
    base_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    logistics_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    margin_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("15.00"))
    margin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_quote_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))

    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus, name="quote_status", native_enum=False),
        nullable=False,
        default=QuoteStatus.DRAFT,
    )

    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    deal: Mapped["Deal"] = relationship("Deal", lazy="joined")
    approver: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<DealQuote id={self.id} incoterm={self.incoterm} total={self.total_quote_price} {self.currency} status={self.status}>"
