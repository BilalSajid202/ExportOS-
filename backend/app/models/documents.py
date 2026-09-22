"""
Tradeloop — Document Generation & Management Models (Phases 10 & 11)

Entities:
- DocumentSet: Grouping of all export documents generated for a specific deal revision.
- GeneratedDocument: Individual document (Proforma Invoice, Commercial Invoice, Packing List, Certificate of Origin)
  with structured JSON content and cryptographic SHA-256 integrity hash.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.organisation import Organisation
    from app.models.user import User


class DocumentType(str, enum.Enum):
    PROFORMA_INVOICE = "PROFORMA_INVOICE"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    CERTIFICATE_OF_ORIGIN = "CERTIFICATE_OF_ORIGIN"


class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class DocumentSet(BaseModel):
    """Set of all export documents produced for a deal revision."""

    __tablename__ = "document_sets"

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

    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_set_status", native_enum=False),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    deal: Mapped["Deal"] = relationship("Deal", lazy="joined")
    documents: Mapped[List["GeneratedDocument"]] = relationship(
        "GeneratedDocument",
        back_populates="document_set",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DocumentSet id={self.id} deal={self.deal_id} rev={self.revision_number} status={self.status}>"


class GeneratedDocument(BaseModel):
    """Single export document artifact with structured data and integrity hash."""

    __tablename__ = "generated_documents"

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

    document_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=False),
        nullable=False,
    )

    document_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="generated_document_status", native_enum=False),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )

    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    document_set: Mapped["DocumentSet"] = relationship("DocumentSet", back_populates="documents", lazy="joined")
    deal: Mapped["Deal"] = relationship("Deal", lazy="joined")
    approver: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<GeneratedDocument id={self.id} type={self.doc_type} num='{self.document_number}'>"
