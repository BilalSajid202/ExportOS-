"""
Tradeloop — Inventory API Routes

Endpoints:
  - GET    /inventory                           - List inventory items for organisation
  - POST   /inventory                           - Create / initialize inventory item for a product (Add)
  - GET    /inventory/{product_id}              - Get single product inventory
  - PUT    /inventory/{product_id}              - Update inventory reorder level & metadata (Update)
  - DELETE /inventory/{product_id}              - Delete inventory item (Remove)
  - POST   /inventory/adjust                    - Adjust stock quantity (Signed delta: +in / -out)
  - GET    /inventory/{product_id}/availability - Check availability for a specific requested quantity
  - POST   /inventory/{product_id}/reserve      - Reserve stock for a product / deal
  - POST   /inventory/reservations/{res_id}/release - Release stock reservation
  - GET    /inventory/{product_id}/transactions - Audit list of stock movements / ledger
  - GET    /inventory/dispatch-history          - View deal fulfillment history (which things sent to whom)
"""

from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.costing import DealQuote, QuoteStatus
from app.models.deal import Deal, DealLineItem, DealState
from app.models.inventory import (
    InventoryItem,
    InventoryReservation,
    InventoryTransaction,
    InventoryTransactionType,
    ReservationStatus,
)
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.inventory import (
    AvailabilityRequest,
    AvailabilityResponse,
    DealDispatchHistoryResponse,
    DispatchItemDetail,
    InventoryAdjustRequest,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryTransactionResponse,
    ReservationResponse,
    ReserveRequest,
)
from app.services import inventory as inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])

_STOCK_WRITERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.ACCOUNTS,
)


@router.get(
    "",
    response_model=List[InventoryItemResponse],
    summary="List inventory for the organisation",
)
async def list_inventory(
    low_stock_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InventoryItemResponse]:
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.product))
        .where(InventoryItem.organisation_id == current_user.organisation_id)
        .order_by(InventoryItem.sku.asc())
    )
    items = result.scalars().all()
    responses = [
        InventoryItemResponse(**inventory_service.to_inventory_item_response_data(i))
        for i in items
    ]
    if low_stock_only:
        responses = [r for r in responses if r.is_low_stock]
    return responses


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add / initialize an inventory item for a product",
)
async def create_inventory_item(
    payload: InventoryItemCreate,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    # 1. Validate product belongs to tenant
    product = await inventory_service.get_product_for_org(
        db, current_user.organisation_id, payload.product_id
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this organisation",
        )

    # 2. Check if already exists
    existing = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, payload.product_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inventory for product {product.sku} already exists. Use adjust stock instead.",
        )

    # 3. Create InventoryItem
    item = InventoryItem(
        organisation_id=current_user.organisation_id,
        product_id=product.id,
        sku=product.sku,
        current_quantity=payload.initial_quantity,
        reserved_quantity=Decimal("0.00"),
        reorder_level=payload.reorder_level,
        unit_of_measure=product.unit_of_measure,
    )
    db.add(item)
    await db.flush()

    if payload.initial_quantity > 0:
        tx = InventoryTransaction(
            organisation_id=current_user.organisation_id,
            inventory_item_id=item.id,
            transaction_type=InventoryTransactionType.RECEIPT,
            quantity=payload.initial_quantity,
            reference_type="INITIAL_SETUP",
            notes=payload.notes or "Initial stock creation",
            created_by=current_user.id,
        )
        db.add(tx)

    await db.commit()
    await db.refresh(item)
    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(item))


@router.get(
    "/dispatch-history",
    response_model=List[DealDispatchHistoryResponse],
    summary="View deal fulfillment history showing which products were sent to whom",
)
async def get_dispatch_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DealDispatchHistoryResponse]:
    """
    Returns history of completed, confirmed, and shipped deals detailing:
      - Who the buyer is
      - Which products were dispatched
      - Quantities and values
      - Incoterms and destinations
    """
    res = await db.execute(
        select(Deal)
        .options(
            selectinload(Deal.line_items).selectinload(DealLineItem.product),
        )
        .where(
            Deal.organisation_id == current_user.organisation_id,
            Deal.state.in_([
                DealState.CONFIRMED,
                DealState.IN_PRODUCTION,
                DealState.DOCS_READY,
                DealState.SHIPPED,
                DealState.PAID,
                DealState.CLOSED,
            ]),
        )
        .order_by(Deal.updated_at.desc())
    )
    deals = res.scalars().all()

    out = []
    for d in deals:
        # Fetch quote info if available
        q_res = await db.execute(
            select(DealQuote)
            .where(
                DealQuote.deal_id == d.id,
                DealQuote.organisation_id == current_user.organisation_id,
            )
            .order_by(DealQuote.created_at.desc())
        )
        quotes = q_res.scalars().all()
        active_q = next((q for q in quotes if q.status == QuoteStatus.APPROVED), quotes[0] if quotes else None)

        items_sent = []
        for li in d.line_items:
            items_sent.append(
                DispatchItemDetail(
                    product_id=li.product_id,
                    sku=li.product.sku if li.product else "SKU",
                    product_name=li.product.name if li.product else "Product",
                    quantity=li.quantity,
                    unit_of_measure=li.product.unit_of_measure if li.product else "PCS",
                    description=li.description,
                )
            )

        out.append(
            DealDispatchHistoryResponse(
                deal_id=d.id,
                reference=d.reference,
                buyer_name=d.buyer_name,
                state=d.state,
                items_sent=items_sent,
                incoterm=active_q.incoterm.value if active_q else None,
                incoterm_place=active_q.incoterm_place if active_q else None,
                total_amount=active_q.total_quote_price if active_q else None,
                currency=active_q.currency if active_q else "USD",
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )

    return out


@router.get(
    "/{product_id}",
    response_model=InventoryItemResponse,
    summary="Get inventory for a single product",
)
async def get_product_inventory(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    item = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, product_id
    )
    if not item:
        product = await inventory_service.get_product_for_org(
            db, current_user.organisation_id, product_id
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        # Auto-create empty inventory record if missing
        item = await inventory_service.get_or_create_inventory_item(
            db, product
        )
        await db.commit()

    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(item))


@router.put(
    "/{product_id}",
    response_model=InventoryItemResponse,
    summary="Update inventory item settings (reorder level, unit of measure)",
)
async def update_inventory_item(
    product_id: UUID,
    payload: InventoryItemUpdate,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    item = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, product_id
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    if payload.reorder_level is not None:
        item.reorder_level = payload.reorder_level
    if payload.unit_of_measure is not None:
        item.unit_of_measure = payload.unit_of_measure.strip()

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(item))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
async def delete_inventory_item(
    product_id: UUID,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
):
    item = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, product_id
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    if item.reserved_quantity > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete inventory for {item.sku}: {item.reserved_quantity} units are currently reserved on active deals.",
        )

    await db.delete(item)
    await db.commit()


@router.post(
    "/adjust",
    response_model=InventoryItemResponse,
    summary="Adjust stock quantity for a product",
)
async def adjust_inventory(
    payload: InventoryAdjustRequest,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    try:
        item = await inventory_service.adjust_stock(
            db,
            organisation_id=current_user.organisation_id,
            product_id=payload.product_id,
            quantity_delta=payload.quantity_delta,
            user=current_user,
            notes=payload.notes,
            reorder_level=payload.reorder_level,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.product))
        .where(InventoryItem.id == item.id)
    )
    reloaded = result.scalar_one()
    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(reloaded))


@router.get(
    "/{product_id}/availability",
    response_model=AvailabilityResponse,
    summary="Check availability for a requested quantity",
)
async def check_availability(
    product_id: UUID,
    requested_quantity: Decimal = Query(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    try:
        data = await inventory_service.check_product_availability(
            db,
            organisation_id=current_user.organisation_id,
            product_id=product_id,
            requested_quantity=requested_quantity,
        )
        await db.commit()
        return AvailabilityResponse(**data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{product_id}/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve stock for a product",
)
async def reserve_stock_endpoint(
    product_id: UUID,
    payload: ReserveRequest,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    if payload.deal_id:
        deal_result = await db.execute(
            select(Deal).where(
                Deal.id == payload.deal_id,
                Deal.organisation_id == current_user.organisation_id,
            )
        )
        if not deal_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

    try:
        res = await inventory_service.reserve_stock(
            db,
            organisation_id=current_user.organisation_id,
            product_id=product_id,
            quantity=payload.quantity,
            user=current_user,
            deal_id=payload.deal_id,
            notes=payload.notes,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    item = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, product_id
    )
    return ReservationResponse(
        id=res.id,
        organisation_id=res.organisation_id,
        inventory_item_id=res.inventory_item_id,
        deal_id=res.deal_id,
        quantity=res.quantity,
        status=res.status,
        created_by=res.created_by,
        created_at=res.created_at,
        released_at=res.released_at,
        sku=item.sku if item else None,
        product_name=item.product.name if (item and item.product) else None,
    )


@router.post(
    "/reservations/{reservation_id}/release",
    response_model=ReservationResponse,
    summary="Release an active stock reservation",
)
async def release_stock_endpoint(
    reservation_id: UUID,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    try:
        res = await inventory_service.release_reservation(
            db,
            organisation_id=current_user.organisation_id,
            reservation_id=reservation_id,
            user=current_user,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return ReservationResponse(
        id=res.id,
        organisation_id=res.organisation_id,
        inventory_item_id=res.inventory_item_id,
        deal_id=res.deal_id,
        quantity=res.quantity,
        status=res.status,
        created_by=res.created_by,
        created_at=res.created_at,
        released_at=res.released_at,
    )


@router.get(
    "/{product_id}/transactions",
    response_model=List[InventoryTransactionResponse],
    summary="Get stock transaction history for a product",
)
async def get_product_transactions(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InventoryTransactionResponse]:
    item = await inventory_service.get_inventory_item(
        db, current_user.organisation_id, product_id
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    txs = await inventory_service.get_inventory_transactions(
        db, current_user.organisation_id, item.id
    )
    return [
        InventoryTransactionResponse(
            id=t.id,
            organisation_id=t.organisation_id,
            inventory_item_id=t.inventory_item_id,
            transaction_type=t.transaction_type,
            quantity=t.quantity,
            reference_type=t.reference_type,
            reference_id=t.reference_id,
            notes=t.notes,
            created_by=t.created_by,
            created_at=t.created_at,
            sku=item.sku,
            product_name=item.product.name if item.product else None,
        )
        for t in txs
    ]
