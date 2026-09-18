"""
ExportOS — Compliance & HS Code Classification Models

Enforces deterministic regulatory checks (SBP Foreign Exchange Manual,
Pakistan Single Window, TDAP, destination customs) and tracks AI-suggested
vs human-confirmed HS codes with full provenance.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.organisation import Organisation
    from app.models.product import Product
    from app.models.user import User


class ComplianceStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    OBTAINED = "OBTAINED"
    WAIVED = "WAIVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplianceCategory(str, enum.Enum):
    REGULATORY_SBP = "REGULATORY_SBP"
    DESTINATION_CUSTOMS = "DESTINATION_CUSTOMS"
    DOCUMENTARY_MANDATORY = "DOCUMENTARY_MANDATORY"
    PAYMENT_TERMS = "PAYMENT_TERMS"
    SHIPPING_CUSTOMS = "SHIPPING_CUSTOMS"


class HSClassificationStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ComplianceCheck(BaseModel):
    """
    Individual regulatory compliance check item bound to a deal.
    """

    __tablename__ = "compliance_checks"

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

    rule_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    category: Mapped[ComplianceCategory] = mapped_column(
        Enum(ComplianceCategory, name="compliance_category", native_enum=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    authority: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status", native_enum=False),
        default=ComplianceStatus.NOT_STARTED,
        nullable=False,
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    responsible_role: Mapped[str] = mapped_column(
        String(50), default="DOCUMENTATION_OFFICER", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    deal: Mapped["Deal"] = relationship("Deal", lazy="joined")
    completer: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<ComplianceCheck id={self.id} rule='{self.rule_code}' "
            f"status='{self.status}' mandatory={self.is_mandatory}>"
        )


class HSCodeClassification(BaseModel):
    """
    Tracks AI-suggested and human-confirmed HS codes for products and deals.
    """

    __tablename__ = "hs_code_classifications"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    suggested_code: Mapped[str] = mapped_column(String(20), nullable=False)
    confirmed_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    heading_title: Mapped[str] = mapped_column(String(255), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("0.85"), nullable=False
    )
    tariff_source: Mapped[str] = mapped_column(
        String(255),
        default="Pakistan Customs Tariff (PCT) 2024-25 / WCO Harmonized System",
        nullable=False,
    )
    status: Mapped[HSClassificationStatus] = mapped_column(
        Enum(
            HSClassificationStatus,
            name="hs_classification_status",
            native_enum=False,
        ),
        default=HSClassificationStatus.SUGGESTED,
        nullable=False,
    )
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    deal: Mapped[Optional["Deal"]] = relationship("Deal", lazy="joined")
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="joined")
    confirmer: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<HSCodeClassification id={self.id} code='{self.suggested_code}' "
            f"status='{self.status}' confidence={self.confidence}>"
        )
