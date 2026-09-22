"""
Tradeloop — Shipment Logistics & Payment API Endpoints (Phase 13)
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.logistics import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
    ShipmentSummaryResponse,
    MilestoneUpdate,
    MilestoneResponse,
    PaymentCreate,
    PaymentResponse,
    DealPaymentSummary,
    ReceivablesAgingReport,
)
from app.services.shipment import (
    create_shipment_for_deal,
    update_shipment_details,
    update_milestone_status,
    get_shipments_for_deal,
    get_active_shipments_summary,
)
from app.services.payment import (
    record_payment_transaction,
    get_deal_payment_summary,
    get_receivables_aging_report,
)

router = APIRouter(prefix="", tags=["Shipment & Payment"])


# ── Shipments & Milestones ─────────────────────────────────────

@router.get("/shipments/deals/{deal_id}", response_model=List[ShipmentResponse])
async def list_deal_shipments(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all shipments and milestone timelines for a deal."""
    return await get_shipments_for_deal(db, deal_id, current_user.organisation_id)


@router.post(
    "/shipments/deals/{deal_id}",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shipment(
    deal_id: UUID,
    payload: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.DOCUMENTATION_OFFICER, UserRole.SALES)
    ),
):
    """Create a new export shipment with automatic Incoterm milestone sequence."""
    try:
        return await create_shipment_for_deal(db, deal_id, current_user.organisation_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/shipments/summary", response_model=ShipmentSummaryResponse)
async def get_shipment_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active shipments overview and milestone health metrics."""
    return await get_active_shipments_summary(db, current_user.organisation_id)


@router.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: UUID,
    payload: ShipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.DOCUMENTATION_OFFICER)
    ),
):
    """Update shipment carrier details, container info, or status."""
    try:
        return await update_shipment_details(db, shipment_id, current_user.organisation_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/shipments/{shipment_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    shipment_id: UUID,
    milestone_id: UUID,
    payload: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.DOCUMENTATION_OFFICER)
    ),
):
    """Update milestone completion status, actual timestamp, and calculate schedule variance."""
    try:
        return await update_milestone_status(db, shipment_id, milestone_id, current_user.organisation_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Payments & Receivables Aging ───────────────────────────────

@router.get("/payments/deals/{deal_id}", response_model=DealPaymentSummary)
async def get_payment_summary(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get deal payment ledger, invoice balance, and SBP 120-day realization countdown."""
    try:
        return await get_deal_payment_summary(db, deal_id, current_user.organisation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/payments/deals/{deal_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    deal_id: UUID,
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.ACCOUNTS)
    ),
):
    """Record an advance payment, LC drawing, or settlement receipt."""
    try:
        return await record_payment_transaction(db, deal_id, current_user.organisation_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/payments/receivables/aging", response_model=ReceivablesAgingReport)
async def get_receivables_aging(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.ACCOUNTS)
    ),
):
    """Organization-wide export receivables aging report with SBP 120-day limit indicators."""
    return await get_receivables_aging_report(db, current_user.organisation_id)
