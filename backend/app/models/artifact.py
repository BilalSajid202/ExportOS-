"""
ExportOS — Artifact & Inbound Inquiry Model

Stores immutable records of all inbound and outbound files, raw emails, and customer artifacts.
Maintains cryptographic SHA-256 hashes for audit trail compliance.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.organisation import Organisation
    from app.models.user import User


class ArtifactType(str, enum.Enum):
    """Classification of the stored artifact."""
    INBOUND_INQUIRY = "INBOUND_INQUIRY"
    QUOTATION = "QUOTATION"
    PROFORMA_INVOICE = "PROFORMA_INVOICE"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    CERTIFICATE = "CERTIFICATE"
    OTHER = "OTHER"


class InboundChannel(str, enum.Enum):
    """Source channel through which an inquiry was received."""
    FILE_UPLOAD = "FILE_UPLOAD"
    EMAIL = "EMAIL"
    WEB_FORM = "WEB_FORM"


class Artifact(BaseModel):
    """
    Immutable record for uploaded documents, raw inquiries, and generated files.
    """

    __tablename__ = "artifacts"

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

    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, name="artifact_type_enum", native_enum=False),
        default=ArtifactType.INBOUND_INQUIRY,
        nullable=False,
    )

    channel: Mapped[InboundChannel] = mapped_column(
        Enum(InboundChannel, name="inbound_channel_enum", native_enum=False),
        default=InboundChannel.FILE_UPLOAD,
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # For raw text / email content
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sender_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    deal: Mapped[Optional["Deal"]] = relationship("Deal", lazy="joined")
    creator: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} filename='{self.filename}' type={self.artifact_type}>"
