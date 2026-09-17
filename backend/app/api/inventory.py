"""
ExportOS — Inventory API Routes

Endpoints:
  GET  /inventory
  GET  /inventory/{product_id}
  POST /inventory/adjust
  GET  /inventory/{product_id}/availability
  POST /inventory/{product_id}/reserve
  POST /inventory/reservations/{reservation_id}/release
  GET  /inventory/{product_id}/transactions
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.deal import Deal
from app.models.inventory import InventoryItem, InventoryReservation, InventoryTransaction
from app.models.user import User, UserRole
from app.schemas.inventory import (
    AvailabilityRequest,
    AvailabilityResponse,
    InventoryAdjustRequest,
    InventoryItemResponse,
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
    item = result.scalar_one()
    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(item))


@router.post(
    "/reservations/{reservation_id}/release",
    response_model=ReservationResponse,
    summary="Release an active reservation",
)
async def release_inventory_reservation(
    reservation_id: UUID,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    try:
        reservation = await inventory_service.release_reservation(
            db,
            organisation_id=current_user.organisation_id,
            reservation_id=reservation_id,
            user=current_user,
        )
        await db.commit()
        await db.refresh(reservation)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = await db.execute(
        select(InventoryReservation)
        .options(
            selectinload(InventoryReservation.inventory_item).selectinload(
                InventoryItem.product
            )
        )
        .where(InventoryReservation.id == reservation.id)
    )
    reservation = result.scalar_one()
    item = reservation.inventory_item
    return ReservationResponse(
        id=reservation.id,
        organisation_id=reservation.organisation_id,
        inventory_item_id=reservation.inventory_item_id,
        deal_id=reservation.deal_id,
        quantity=reservation.quantity,
        status=reservation.status,
        created_by=reservation.created_by,
        created_at=reservation.created_at,
        released_at=reservation.released_at,
        sku=item.sku if item else None,
        product_name=item.product.name if item and item.product else None,
    )


@router.get(
    "/{product_id}",
    response_model=InventoryItemResponse,
    summary="Get inventory for a product",
)
async def get_inventory_for_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    try:
        product = await inventory_service.get_product_for_org(
            db, current_user.organisation_id, product_id
        )
        if not product:
            raise ValueError("Product not found in this organisation")
        item = await inventory_service.get_or_create_inventory_item(db, product)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.product))
        .where(InventoryItem.id == item.id)
    )
    item = result.scalar_one()
    return InventoryItemResponse(**inventory_service.to_inventory_item_response_data(item))


@router.get(
    "/{product_id}/availability",
    response_model=AvailabilityResponse,
    summary="Check availability for a requested quantity",
)
async def check_availability(
    product_id: UUID,
    requested_quantity: float = Query(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    from decimal import Decimal

    try:
        data = await inventory_service.check_product_availability(
            db,
            organisation_id=current_user.organisation_id,
            product_id=product_id,
            requested_quantity=Decimal(str(requested_quantity)),
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return AvailabilityResponse(
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


@router.post(
    "/{product_id}/availability",
    response_model=AvailabilityResponse,
    summary="Check availability (JSON body)",
)
async def check_availability_post(
    product_id: UUID,
    payload: AvailabilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    try:
        data = await inventory_service.check_product_availability(
            db,
            organisation_id=current_user.organisation_id,
            product_id=product_id,
            requested_quantity=payload.requested_quantity,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return AvailabilityResponse(
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


@router.post(
    "/{product_id}/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve inventory for a product",
)
async def reserve_inventory(
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deal not found in this organisation",
            )

    try:
        reservation = await inventory_service.reserve_stock(
            db,
            organisation_id=current_user.organisation_id,
            product_id=product_id,
            quantity=payload.quantity,
            user=current_user,
            deal_id=payload.deal_id,
            notes=payload.notes,
        )
        await db.commit()
        await db.refresh(reservation)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = await db.execute(
        select(InventoryReservation)
        .options(
            selectinload(InventoryReservation.inventory_item).selectinload(
                InventoryItem.product
            )
        )
        .where(InventoryReservation.id == reservation.id)
    )
    reservation = result.scalar_one()
    item = reservation.inventory_item
    return ReservationResponse(
        id=reservation.id,
        organisation_id=reservation.organisation_id,
        inventory_item_id=reservation.inventory_item_id,
        deal_id=reservation.deal_id,
        quantity=reservation.quantity,
        status=reservation.status,
        created_by=reservation.created_by,
        created_at=reservation.created_at,
        released_at=reservation.released_at,
        sku=item.sku if item else None,
        product_name=item.product.name if item and item.product else None,
    )


@router.post(
    "/reservations/{reservation_id}/release",
    response_model=ReservationResponse,
    summary="Release an active reservation",
)
async def release_inventory_reservation(
    reservation_id: UUID,
    current_user: User = Depends(_STOCK_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    try:
        reservation = await inventory_service.release_reservation(
            db,
            organisation_id=current_user.organisation_id,
            reservation_id=reservation_id,
            user=current_user,
        )
        await db.commit()
        await db.refresh(reservation)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = await db.execute(
        select(InventoryReservation)
        .options(
            selectinload(InventoryReservation.inventory_item).selectinload(
                InventoryItem.product
            )
        )
        .where(InventoryReservation.id == reservation.id)
    )
    reservation = result.scalar_one()
    item = reservation.inventory_item
    return ReservationResponse(
        id=reservation.id,
        organisation_id=reservation.organisation_id,
        inventory_item_id=reservation.inventory_item_id,
        deal_id=reservation.deal_id,
        quantity=reservation.quantity,
        status=reservation.status,
        created_by=reservation.created_by,
        created_at=reservation.created_at,
        released_at=reservation.released_at,
        sku=item.sku if item else None,
        product_name=item.product.name if item and item.product else None,
    )


@router.get(
    "/{product_id}/transactions",
    response_model=List[InventoryTransactionResponse],
    summary="List stock transactions for a product",
)
async def list_transactions(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InventoryTransactionResponse]:
    product = await inventory_service.get_product_for_org(
        db, current_user.organisation_id, product_id
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    item_result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.product_id == product_id,
            InventoryItem.organisation_id == current_user.organisation_id,
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        return []

    tx_result = await db.execute(
        select(InventoryTransaction)
        .where(
            InventoryTransaction.inventory_item_id == item.id,
            InventoryTransaction.organisation_id == current_user.organisation_id,
        )
        .order_by(InventoryTransaction.created_at.desc())
    )
    txs = tx_result.scalars().all()
    return [InventoryTransactionResponse.model_validate(t) for t in txs]
