"""
Tradeloop — Deal Management, State Machine, Costing & Quotation API (Phases 3, 4, 7, 8)

Endpoints:
  - POST   /deals                           - Create manual deal
  - GET    /deals                           - List tenant deals
  - GET    /deals/{deal_id}                 - Get deal details
  - POST   /deals/{deal_id}/transition      - Execute state transition with audit trail
  - GET    /deals/{deal_id}/availability    - Check stock availability and shortfall
  - POST   /deals/{deal_id}/reserve         - Reserve stock for line items
  - POST   /deals/{deal_id}/resolve-shortfall - Apply commercial decision to shortfall
  - GET    /deals/{deal_id}/costing         - Get costing sheet and active quote
  - POST   /deals/{deal_id}/costing         - Add cost breakdown component
  - DELETE /deals/{deal_id}/costing/{comp_id} - Delete cost component
  - POST   /deals/{deal_id}/quote           - Calculate deterministic Incoterm quote
  - POST   /deals/{deal_id}/quote/approve   - Managerial approval of quote (transitions to QUOTED)
  - GET    /deals/{deal_id}/audit-trail     - View complete chronological audit history
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.audit import AuditEntry
from app.models.costing import (
    CostComponent,
    DealQuote,
    Incoterm,
    QuoteStatus,
)
from app.models.deal import Deal, DealLineItem, DealState
from app.models.inventory import AvailabilityStatus
from app.models.user import User, UserRole
from app.schemas.costing import (
    CostComponentCreate,
    CostComponentResponse,
    DealCostingSummaryResponse,
    QuoteApproveRequest,
    QuoteCalculateRequest,
    QuoteResponse,
)
from app.schemas.deal import (
    AuditEntryResponse,
    DealCreateRequest,
    DealLineItemResponse,
    DealResponse,
    DealTransitionRequest,
    ShortfallAction,
    ShortfallResolveRequest,
)
from app.schemas.inventory import DealAvailabilityLine, DealAvailabilityResponse
from app.services import costing as costing_service
from app.services import deal_state as deal_state_service
from app.services import inventory as inventory_service

router = APIRouter(prefix="/deals", tags=["Deals"])

_DEAL_WRITERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.SALES,
)

_APPROVERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
)


def _serialize_deal(deal: Deal) -> DealResponse:
    lines = []
    for li in deal.line_items:
        lines.append(
            DealLineItemResponse(
                id=li.id,
                organisation_id=li.organisation_id,
                deal_id=li.deal_id,
                product_id=li.product_id,
                quantity=li.quantity,
                description=li.description,
                product_sku=li.product.sku if li.product else None,
                product_name=li.product.name if li.product else None,
                created_at=li.created_at,
            )
        )
    return DealResponse(
        id=deal.id,
        organisation_id=deal.organisation_id,
        reference=deal.reference,
        buyer_name=deal.buyer_name,
        state=deal.state,
        notes=deal.notes,
        created_by=deal.created_by,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        line_items=lines,
    )


async def _next_reference(db: AsyncSession, organisation_id: UUID) -> str:
    year = datetime.now(timezone.utc).year
    count_result = await db.execute(
        select(func.count())
        .select_from(Deal)
        .where(Deal.organisation_id == organisation_id)
    )
    count = count_result.scalar_one() + 1
    return f"EO-{year}-{count:04d}"


async def _get_tenant_deal(
    db: AsyncSession,
    organisation_id: UUID,
    deal_id: UUID,
) -> Deal:
    result = await db.execute(
        select(Deal)
        .options(
            selectinload(Deal.line_items).selectinload(DealLineItem.product),
            selectinload(Deal.reservations),
        )
        .where(
            Deal.id == deal_id,
            Deal.organisation_id == organisation_id,
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return deal


# ── Deal CRUD & State Machine ──────────────────────────────────

@router.post(
    "",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual deal with line items",
)
async def create_deal(
    payload: DealCreateRequest,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    # Validate all products belong to tenant
    for line in payload.line_items:
        product = await inventory_service.get_product_for_org(
            db, current_user.organisation_id, line.product_id
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {line.product_id} not found in this organisation",
            )

    reference = await _next_reference(db, current_user.organisation_id)
    deal = Deal(
        organisation_id=current_user.organisation_id,
        reference=reference,
        buyer_name=payload.buyer_name.strip(),
        state=DealState.INQUIRY,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(deal)
    await db.flush()

    for line in payload.line_items:
        db.add(
            DealLineItem(
                organisation_id=current_user.organisation_id,
                deal_id=deal.id,
                product_id=line.product_id,
                quantity=line.quantity,
                description=line.description,
            )
        )

    # Initial audit log
    await deal_state_service.record_audit_entry(
        db=db,
        organisation_id=current_user.organisation_id,
        deal_id=deal.id,
        user=current_user,
        action="DEAL_CREATED",
        from_state=None,
        to_state=DealState.INQUIRY.value,
        details={"buyer_name": deal.buyer_name, "reference": reference},
        notes="Deal initiated",
    )

    await db.commit()
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal.id)
    return _serialize_deal(deal)


@router.get(
    "",
    response_model=List[DealResponse],
    summary="List deals for the organisation",
)
async def list_deals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DealResponse]:
    result = await db.execute(
        select(Deal)
        .options(
            selectinload(Deal.line_items).selectinload(DealLineItem.product),
        )
        .where(Deal.organisation_id == current_user.organisation_id)
        .order_by(Deal.created_at.desc())
    )
    deals = result.scalars().all()
    return [_serialize_deal(d) for d in deals]


@router.get(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Get deal details",
)
async def get_deal(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    return _serialize_deal(deal)


@router.post(
    "/{deal_id}/transition",
    response_model=DealResponse,
    summary="Execute state machine transition on a deal",
)
async def transition_deal(
    deal_id: UUID,
    payload: DealTransitionRequest,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Transitions deal state with validation and audit logging."""
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    updated_deal = await deal_state_service.transition_deal_state(
        db=db,
        deal=deal,
        target_state=payload.target_state,
        user=current_user,
        reason=payload.reason,
        extra_details=payload.details,
    )
    return _serialize_deal(updated_deal)


@router.post(
    "/{deal_id}/confirm",
    response_model=DealResponse,
    summary="Confirm deal order and trigger stock allocation/reservation",
)
async def confirm_deal(
    deal_id: UUID,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> DealResponse:
    """
    Phase 9 Order Confirmation:
      1. Transitions deal state to CONFIRMED
      2. Attempts stock reservation for available line items
      3. Records confirmation in audit trail
    """
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)

    # 1. Transition to CONFIRMED
    updated_deal = await deal_state_service.transition_deal_state(
        db=db,
        deal=deal,
        target_state=DealState.CONFIRMED,
        user=current_user,
        reason="Order confirmed by buyer / signed proforma invoice",
    )

    # 2. Try auto-reserving stock if all lines are available
    can_reserve = True
    for li in updated_deal.line_items:
        data = await inventory_service.check_product_availability(
            db,
            organisation_id=current_user.organisation_id,
            product_id=li.product_id,
            requested_quantity=li.quantity,
        )
        if data["status"] != AvailabilityStatus.AVAILABLE:
            can_reserve = False
            break

    if can_reserve:
        for li in updated_deal.line_items:
            await inventory_service.reserve_stock(
                db,
                organisation_id=current_user.organisation_id,
                product_id=li.product_id,
                quantity=li.quantity,
                user=current_user,
                deal_id=updated_deal.id,
                notes=f"Auto-reserved upon order confirmation for {updated_deal.reference}",
            )
        await db.commit()

    return _serialize_deal(updated_deal)


# ── Inventory Availability & Shortfall Actions ─────────────────

@router.get(
    "/{deal_id}/availability",
    response_model=DealAvailabilityResponse,
    summary="Check inventory availability for all deal line items",
)
async def get_deal_availability(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealAvailabilityResponse:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    lines: List[DealAvailabilityLine] = []
    worst = AvailabilityStatus.AVAILABLE

    for li in deal.line_items:
        try:
            data = await inventory_service.check_product_availability(
                db,
                organisation_id=current_user.organisation_id,
                product_id=li.product_id,
                requested_quantity=li.quantity,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        lines.append(
            DealAvailabilityLine(
                product_id=data["product_id"],
                sku=data["sku"],
                product_name=data["product_name"],
                requested_quantity=data["requested_quantity"],
                current_quantity=data["current_quantity"],
                reserved_quantity=data["reserved_quantity"],
                available_quantity=data["available_quantity"],
                shortfall=data["shortfall"],
                status=data["status"],
                unit_of_measure=data["unit_of_measure"],
                message=data["message"],
            )
        )
        if data["status"] == AvailabilityStatus.UNAVAILABLE:
            worst = AvailabilityStatus.UNAVAILABLE
        elif (
            data["status"] == AvailabilityStatus.PARTIALLY_AVAILABLE
            and worst == AvailabilityStatus.AVAILABLE
        ):
            worst = AvailabilityStatus.PARTIALLY_AVAILABLE

    await db.commit()
    return DealAvailabilityResponse(
        deal_id=deal.id,
        reference=deal.reference,
        buyer_name=deal.buyer_name,
        overall_status=worst,
        lines=lines,
    )


@router.post(
    "/{deal_id}/resolve-shortfall",
    response_model=DealAvailabilityResponse,
    summary="Apply human commercial decision to deal shortfall",
)
async def resolve_deal_shortfall(
    deal_id: UUID,
    payload: ShortfallResolveRequest,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> DealAvailabilityResponse:
    """
    Handles employee choice when stock is insufficient:
      - REDUCE_TO_AVAILABLE: Adjust line item quantity to matched available inventory.
      - ACCEPT_FOR_PRODUCTION: Keep requested quantity and mark deal for production/procurement.
    """
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)

    # Find target line item
    target_line = next((li for li in deal.line_items if li.product_id == payload.product_id), None)
    if not target_line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this deal's line items",
        )

    avail_info = await inventory_service.check_product_availability(
        db,
        organisation_id=current_user.organisation_id,
        product_id=payload.product_id,
        requested_quantity=target_line.quantity,
    )

    if payload.action == ShortfallAction.REDUCE_TO_AVAILABLE:
        new_qty = payload.custom_quantity or avail_info["available_quantity"]
        if new_qty <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Available quantity is 0. Cannot reduce to 0, please mark for production or cancel.",
            )
        old_qty = target_line.quantity
        target_line.quantity = new_qty
        db.add(target_line)

        await deal_state_service.record_audit_entry(
            db=db,
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            user=current_user,
            action="SHORTFALL_REDUCED",
            from_state=deal.state.value,
            to_state=deal.state.value,
            details={
                "product_id": str(payload.product_id),
                "sku": avail_info["sku"],
                "old_quantity": str(old_qty),
                "new_quantity": str(new_qty),
            },
            notes=f"Reduced quantity to match available inventory: {new_qty} {avail_info['unit_of_measure']}",
        )

    elif payload.action == ShortfallAction.ACCEPT_FOR_PRODUCTION:
        if deal.state in {DealState.INQUIRY, DealState.QUOTED, DealState.CONFIRMED}:
            deal.state = DealState.IN_PRODUCTION
            db.add(deal)

        await deal_state_service.record_audit_entry(
            db=db,
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            user=current_user,
            action="SHORTFALL_ACCEPTED_FOR_PRODUCTION",
            from_state=deal.state.value,
            to_state=deal.state.value,
            details={
                "product_id": str(payload.product_id),
                "sku": avail_info["sku"],
                "requested_quantity": str(target_line.quantity),
                "shortfall": str(avail_info["shortfall"]),
            },
            notes=f"Accepted shortfall of {avail_info['shortfall']} {avail_info['unit_of_measure']} for production/procurement",
        )

    await db.commit()
    return await get_deal_availability(deal_id, current_user, db)


@router.post(
    "/{deal_id}/reserve",
    response_model=DealAvailabilityResponse,
    summary="Reserve available stock for all deal line items",
)
async def reserve_deal_inventory(
    deal_id: UUID,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.ACCOUNTS)
    ),
    db: AsyncSession = Depends(get_db),
) -> DealAvailabilityResponse:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)

    # Pre-check all lines
    for li in deal.line_items:
        data = await inventory_service.check_product_availability(
            db,
            organisation_id=current_user.organisation_id,
            product_id=li.product_id,
            requested_quantity=li.quantity,
        )
        if data["status"] != AvailabilityStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reserve {data['sku']}: {data['message']}. "
                    "Reduce quantity or procure shortfall first."
                ),
            )

    try:
        for li in deal.line_items:
            await inventory_service.reserve_stock(
                db,
                organisation_id=current_user.organisation_id,
                product_id=li.product_id,
                quantity=li.quantity,
                user=current_user,
                deal_id=deal.id,
                notes=f"Reserved for deal {deal.reference}",
            )
        
        await deal_state_service.record_audit_entry(
            db=db,
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            user=current_user,
            action="INVENTORY_RESERVED",
            from_state=deal.state.value,
            to_state=deal.state.value,
            details={"deal_reference": deal.reference},
            notes="Reserved inventory for deal line items",
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return await get_deal_availability(deal_id, current_user, db)


# ── Costing & Quotation ────────────────────────────────────────

@router.get(
    "/{deal_id}/costing",
    response_model=DealCostingSummaryResponse,
    summary="Get cost breakdown components and active quote for a deal",
)
async def get_deal_costing(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealCostingSummaryResponse:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    components = await costing_service.get_deal_cost_components(db, current_user.organisation_id, deal.id)
    total_cost = sum(c.amount for c in components) if components else Decimal("0.00")

    # Fetch quotes
    quote_res = await db.execute(
        select(DealQuote)
        .where(
            DealQuote.deal_id == deal.id,
            DealQuote.organisation_id == current_user.organisation_id,
        )
        .order_by(DealQuote.created_at.desc())
    )
    quotes = quote_res.scalars().all()
    active_quote = next((q for q in quotes if q.status == QuoteStatus.APPROVED), None)
    if not active_quote and quotes:
        active_quote = quotes[0]

    return DealCostingSummaryResponse(
        deal_id=deal.id,
        components=[CostComponentResponse.model_validate(c) for c in components],
        total_components_cost=total_cost,
        active_quote=QuoteResponse.model_validate(active_quote) if active_quote else None,
        quotes_history=[QuoteResponse.model_validate(q) for q in quotes],
    )


@router.post(
    "/{deal_id}/costing",
    response_model=CostComponentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a cost breakdown component to a deal",
)
async def add_deal_cost_component(
    deal_id: UUID,
    payload: CostComponentCreate,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> CostComponentResponse:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    component = CostComponent(
        organisation_id=current_user.organisation_id,
        deal_id=deal.id,
        cost_type=payload.cost_type,
        description=payload.description.strip(),
        amount=payload.amount,
        currency=payload.currency.upper(),
        notes=payload.notes,
    )
    db.add(component)
    await db.commit()
    await db.refresh(component)
    return CostComponentResponse.model_validate(component)


@router.delete(
    "/{deal_id}/costing/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cost breakdown component",
)
async def delete_deal_cost_component(
    deal_id: UUID,
    component_id: UUID,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
):
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    res = await db.execute(
        select(CostComponent).where(
            CostComponent.id == component_id,
            CostComponent.deal_id == deal.id,
            CostComponent.organisation_id == current_user.organisation_id,
        )
    )
    comp = res.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost component not found")
    await db.delete(comp)
    await db.commit()


@router.post(
    "/{deal_id}/quote",
    response_model=QuoteResponse,
    summary="Calculate and generate an Incoterm quotation",
)
async def generate_deal_quote(
    deal_id: UUID,
    payload: QuoteCalculateRequest,
    current_user: User = Depends(_DEAL_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """Calculates deterministic quote based on selected Incoterm rules."""
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    quote = await costing_service.calculate_deal_quote(
        db=db,
        deal=deal,
        incoterm=payload.incoterm,
        incoterm_place=payload.incoterm_place,
        margin_percentage=payload.margin_percentage,
        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{deal_id}/quote/approve",
    response_model=QuoteResponse,
    summary="Approve quotation and advance deal to QUOTED status",
)
async def approve_deal_quote(
    deal_id: UUID,
    payload: QuoteApproveRequest,
    current_user: User = Depends(_APPROVERS),
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """
    Managerial approval gateway:
      1. Approves active/latest draft quote
      2. Transitions deal state from INQUIRY -> QUOTED
      3. Records approval in immutable audit trail
    """
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    quote_res = await db.execute(
        select(DealQuote)
        .where(
            DealQuote.deal_id == deal.id,
            DealQuote.organisation_id == current_user.organisation_id,
        )
        .order_by(DealQuote.created_at.desc())
    )
    quote = quote_res.scalars().first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quotation generated yet. Calculate a quote first.",
        )

    quote.status = QuoteStatus.APPROVED
    quote.approved_by = current_user.id
    quote.approved_at = datetime.now(timezone.utc)
    if payload.notes:
        quote.notes = payload.notes
    db.add(quote)

    # Transition deal to QUOTED if still INQUIRY
    if deal.state == DealState.INQUIRY:
        await deal_state_service.transition_deal_state(
            db=db,
            deal=deal,
            target_state=DealState.QUOTED,
            user=current_user,
            reason="Quotation approved by manager",
            extra_details={
                "quote_id": str(quote.id),
                "incoterm": quote.incoterm.value,
                "total_price": str(quote.total_quote_price),
                "currency": quote.currency,
            },
        )
    else:
        await deal_state_service.record_audit_entry(
            db=db,
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            user=current_user,
            action="QUOTE_APPROVED",
            from_state=deal.state.value,
            to_state=deal.state.value,
            details={"quote_id": str(quote.id), "total_price": str(quote.total_quote_price)},
            notes=payload.notes or "Quote approved",
        )
        await db.commit()

    await db.refresh(quote)
    return QuoteResponse.model_validate(quote)


# ── Audit Trail ────────────────────────────────────────────────

@router.get(
    "/{deal_id}/audit-trail",
    response_model=List[AuditEntryResponse],
    summary="Get complete audit history for a deal",
)
async def get_deal_audit_log(
    deal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEntryResponse]:
    deal = await _get_tenant_deal(db, current_user.organisation_id, deal_id)
    entries = await deal_state_service.get_deal_audit_trail(db, current_user.organisation_id, deal.id)
    out = []
    for e in entries:
        out.append(
            AuditEntryResponse(
                id=e.id,
                organisation_id=e.organisation_id,
                deal_id=e.deal_id,
                user_id=e.user_id,
                user_email=e.user.email if e.user else None,
                user_name=f"{e.user.first_name} {e.user.last_name}" if e.user else "System",
                action=e.action,
                from_state=e.from_state,
                to_state=e.to_state,
                details=e.details,
                notes=e.notes,
                created_at=e.created_at,
            )
        )
    return out
