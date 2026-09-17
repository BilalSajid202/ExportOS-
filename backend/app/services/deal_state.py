"""
ExportOS — Deal State Machine & Audit Trail Service (Phase 4)

Enforces strict legal state transitions and records immutable audit entries.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEntry
from app.models.deal import Deal, DealState
from app.models.user import User


# Directed state transition graph
ALLOWED_TRANSITIONS: Dict[DealState, Set[DealState]] = {
    DealState.INQUIRY: {
        DealState.QUOTED,
        DealState.CONFIRMED,  # Direct confirmation if quote bypass allowed
        DealState.CANCELLED,
    },
    DealState.QUOTED: {
        DealState.CONFIRMED,
        DealState.CANCELLED,
    },
    DealState.CONFIRMED: {
        DealState.IN_PRODUCTION,
        DealState.DOCS_READY,
        DealState.CANCELLED,
    },
    DealState.IN_PRODUCTION: {
        DealState.DOCS_READY,
        DealState.CANCELLED,
    },
    DealState.DOCS_READY: {
        DealState.SHIPPED,
        DealState.CANCELLED,
    },
    DealState.SHIPPED: {
        DealState.PAID,
    },
    DealState.PAID: {
        DealState.CLOSED,
    },
    DealState.CLOSED: set(),
    DealState.CANCELLED: set(),
}


async def record_audit_entry(
    db: AsyncSession,
    organisation_id: UUID,
    deal_id: Optional[UUID],
    user: Optional[User],
    action: str,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> AuditEntry:
    """Creates and persists an immutable audit log entry."""
    entry = AuditEntry(
        organisation_id=organisation_id,
        deal_id=deal_id,
        user_id=user.id if user else None,
        action=action,
        from_state=from_state,
        to_state=to_state,
        details=details or {},
        notes=notes,
    )
    db.add(entry)
    await db.flush()
    return entry


async def transition_deal_state(
    db: AsyncSession,
    deal: Deal,
    target_state: DealState,
    user: User,
    reason: Optional[str] = None,
    extra_details: Optional[Dict[str, Any]] = None,
) -> Deal:
    """
    Validates and executes a state transition on a deal.
    Raises 400 Bad Request if the transition violates the state graph.
    """
    current_state = deal.state
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())

    if target_state not in allowed:
        allowed_names = ", ".join(s.value for s in allowed) or "None (Terminal State)"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition deal from {current_state.value} to {target_state.value}. "
                f"Allowed target states: {allowed_names}"
            ),
        )

    deal.state = target_state
    db.add(deal)

    # Record in audit log
    await record_audit_entry(
        db=db,
        organisation_id=deal.organisation_id,
        deal_id=deal.id,
        user=user,
        action="STATE_TRANSITION",
        from_state=current_state.value,
        to_state=target_state.value,
        details={
            "reason": reason,
            **(extra_details or {}),
        },
        notes=reason,
    )

    await db.commit()
    await db.refresh(deal)
    return deal


async def get_deal_audit_trail(
    db: AsyncSession,
    organisation_id: UUID,
    deal_id: UUID,
) -> List[AuditEntry]:
    """Fetches chronological audit trail for a deal."""
    result = await db.execute(
        select(AuditEntry)
        .where(
            AuditEntry.organisation_id == organisation_id,
            AuditEntry.deal_id == deal_id,
        )
        .order_by(AuditEntry.created_at.desc())
    )
    return list(result.scalars().all())
