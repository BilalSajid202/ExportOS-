"""
ExportOS — Audit Log Model (Phase 4 & Phase 8)

Records immutable audit events for state changes, quotation approvals,
inventory actions, and compliance events.
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.organisation import Organisation
    from app.models.user import User


class AuditEntry(BaseModel):
    """Immutable audit trail for actions across deals and inventory."""

    __tablename__ = "audit_entries"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., STATE_TRANSITION, QUOTE_APPROVED, SHORTFALL_RESOLVED
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    deal: Mapped[Optional["Deal"]] = relationship("Deal", lazy="joined")
    user: Mapped[Optional["User"]] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<AuditEntry id={self.id} action={self.action} deal={self.deal_id} user={self.user_id}>"
