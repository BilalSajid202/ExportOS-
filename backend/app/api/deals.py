"""
ExportOS — Minimal Deal API Routes (Phase 3)

Endpoints:
  POST /deals
  GET  /deals
  GET  /deals/{deal_id}
  GET  /deals/{deal_id}/availability
  POST /deals/{deal_id}/reserve
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.deal import Deal, DealLineItem, DealState
from app.models.inventory import AvailabilityStatus
from app.models.user import User, UserRole
from app.schemas.deal import DealCreateRequest, DealLineItemResponse, DealResponse
from app.schemas.inventory import DealAvailabilityLine, DealAvailabilityResponse
from app.services import inventory as inventory_service

router = APIRouter(prefix="/deals", tags=["Deals"])

_DEAL_WRITERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.SALES,
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
    """
    Reserves full requested quantity per line when available.
    Fails the whole request if any line cannot be fully reserved.
    """
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
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return await get_deal_availability(deal_id, current_user, db)
