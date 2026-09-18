"""
ExportOS — Inventory Service

All quantity math is deterministic application code (never LLM).
available = current - reserved
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import (
    AvailabilityStatus,
    InventoryItem,
    InventoryReservation,
    InventoryTransaction,
    InventoryTransactionType,
    ReservationStatus,
)
from app.models.product import Product
from app.models.user import User


def compute_availability(
    current: Decimal,
    reserved: Decimal,
    requested: Decimal,
) -> Tuple[Decimal, Decimal, AvailabilityStatus]:
    """
    Pure function — used by API and tests.

    Returns (available, shortfall, status).
    """
    available = current - reserved
    if available < 0:
        available = Decimal("0")

    if available <= 0:
        return available, requested, AvailabilityStatus.UNAVAILABLE

    if available >= requested:
        return available, Decimal("0"), AvailabilityStatus.AVAILABLE

    shortfall = requested - available
    return available, shortfall, AvailabilityStatus.PARTIALLY_AVAILABLE


def availability_message(
    status: AvailabilityStatus,
    available: Decimal,
    shortfall: Decimal,
    uom: str,
) -> str:
    if status == AvailabilityStatus.AVAILABLE:
        return f"Fully available. {available} {uom} in stock after existing reservations."
    if status == AvailabilityStatus.PARTIALLY_AVAILABLE:
        return (
            f"Not fully available. {available} {uom} are available and "
            f"{shortfall} additional {uom} are required."
        )
    return f"Unavailable. No free stock. Shortfall: {shortfall} {uom}."


async def get_product_for_org(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Optional[Product]:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.organisation_id == organisation_id,
        )
    )
    return result.scalar_one_or_none()


async def get_inventory_item(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Optional[InventoryItem]:
    """Fetch single inventory item for product and org, with product relation loaded."""
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.product))
        .where(
            InventoryItem.product_id == product_id,
            InventoryItem.organisation_id == organisation_id,
        )
    )
    return result.scalar_one_or_none()


async def get_inventory_transactions(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    inventory_item_id: uuid.UUID,
) -> list[InventoryTransaction]:
    """Fetch all stock movement transactions for an inventory item."""
    result = await db.execute(
        select(InventoryTransaction)
        .where(
            InventoryTransaction.inventory_item_id == inventory_item_id,
            InventoryTransaction.organisation_id == organisation_id,
        )
        .order_by(InventoryTransaction.created_at.desc())
    )
    return list(result.scalars().all())


async def get_or_create_inventory_item(
    db: AsyncSession,
    product: Product,
    *,
    for_update: bool = False,
) -> InventoryItem:
    """Fetch inventory row for product; create zero-stock row if missing."""
    query = select(InventoryItem).where(
        InventoryItem.product_id == product.id,
        InventoryItem.organisation_id == product.organisation_id,
    )
    if for_update:
        query = query.with_for_update()

    result = await db.execute(query)
    item = result.scalar_one_or_none()
    if item:
        return item

    item = InventoryItem(
        organisation_id=product.organisation_id,
        product_id=product.id,
        sku=product.sku,
        current_quantity=Decimal("0"),
        reserved_quantity=Decimal("0"),
        reorder_level=Decimal("0"),
        unit_of_measure=product.unit_of_measure,
    )
    db.add(item)
    await db.flush()

    if for_update:
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.id == item.id)
            .with_for_update()
        )
        item = result.scalar_one()

    return item


async def adjust_stock(
    db: AsyncSession,
    *,
    organisation_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity_delta: Decimal,
    user: User,
    notes: Optional[str] = None,
    reorder_level: Optional[Decimal] = None,
) -> InventoryItem:
    product = await get_product_for_org(db, organisation_id, product_id)
    if not product:
        raise ValueError("Product not found in this organisation")

    item = await get_or_create_inventory_item(db, product, for_update=True)

    new_current = item.current_quantity + quantity_delta
    if new_current < 0:
        raise ValueError(
            f"Adjustment would make current stock negative "
            f"(current={item.current_quantity}, delta={quantity_delta})"
        )
    if new_current < item.reserved_quantity:
        raise ValueError(
            f"Adjustment would leave current stock below reserved "
            f"(new_current={new_current}, reserved={item.reserved_quantity})"
        )

    item.current_quantity = new_current
    item.sku = product.sku
    item.unit_of_measure = product.unit_of_measure
    if reorder_level is not None:
        item.reorder_level = reorder_level

    tx_type = (
        InventoryTransactionType.RECEIPT
        if quantity_delta > 0
        else InventoryTransactionType.ADJUSTMENT
    )
    db.add(
        InventoryTransaction(
            organisation_id=organisation_id,
            inventory_item_id=item.id,
            transaction_type=tx_type,
            quantity=quantity_delta,
            reference_type="MANUAL_ADJUST",
            notes=notes,
            created_by=user.id,
        )
    )
    await db.flush()
    return item


async def check_product_availability(
    db: AsyncSession,
    *,
    organisation_id: uuid.UUID,
    product_id: uuid.UUID,
    requested_quantity: Decimal,
) -> dict:
    product = await get_product_for_org(db, organisation_id, product_id)
    if not product:
        raise ValueError("Product not found in this organisation")

    item = await get_or_create_inventory_item(db, product, for_update=False)
    available, shortfall, status = compute_availability(
        item.current_quantity,
        item.reserved_quantity,
        requested_quantity,
    )
    return {
        "product_id": product.id,
        "sku": product.sku,
        "product_name": product.name,
        "requested_quantity": requested_quantity,
        "current_quantity": item.current_quantity,
        "reserved_quantity": item.reserved_quantity,
        "available_quantity": available,
        "shortfall": shortfall,
        "status": status,
        "unit_of_measure": item.unit_of_measure,
        "message": availability_message(status, available, shortfall, item.unit_of_measure),
        "inventory_item": item,
        "product": product,
    }


async def reserve_stock(
    db: AsyncSession,
    *,
    organisation_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: Decimal,
    user: User,
    deal_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
    allow_partial: bool = False,
) -> InventoryReservation:
    """
    Reserve stock for a deal (or standalone).
    By default requires full availability; set allow_partial to reserve only what's free.
    """
    product = await get_product_for_org(db, organisation_id, product_id)
    if not product:
        raise ValueError("Product not found in this organisation")

    item = await get_or_create_inventory_item(db, product, for_update=True)
    available = item.current_quantity - item.reserved_quantity

    reserve_qty = quantity
    if available < quantity:
        if not allow_partial or available <= 0:
            raise ValueError(
                f"Insufficient available stock. Available={available}, requested={quantity}"
            )
        reserve_qty = available

    item.reserved_quantity = item.reserved_quantity + reserve_qty

    reservation = InventoryReservation(
        organisation_id=organisation_id,
        inventory_item_id=item.id,
        deal_id=deal_id,
        quantity=reserve_qty,
        status=ReservationStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(reservation)
    await db.flush()

    db.add(
        InventoryTransaction(
            organisation_id=organisation_id,
            inventory_item_id=item.id,
            transaction_type=InventoryTransactionType.RESERVATION,
            quantity=reserve_qty,
            reference_type="RESERVATION",
            reference_id=reservation.id,
            notes=notes,
            created_by=user.id,
        )
    )
    await db.flush()
    return reservation


async def release_reservation(
    db: AsyncSession,
    *,
    organisation_id: uuid.UUID,
    reservation_id: uuid.UUID,
    user: User,
) -> InventoryReservation:
    result = await db.execute(
        select(InventoryReservation)
        .options(selectinload(InventoryReservation.inventory_item))
        .where(
            InventoryReservation.id == reservation_id,
            InventoryReservation.organisation_id == organisation_id,
        )
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise ValueError("Reservation not found")
    if reservation.status != ReservationStatus.ACTIVE:
        raise ValueError(f"Reservation is not ACTIVE (status={reservation.status})")

    item_result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.id == reservation.inventory_item_id)
        .with_for_update()
    )
    item = item_result.scalar_one()

    item.reserved_quantity = item.reserved_quantity - reservation.quantity
    if item.reserved_quantity < 0:
        item.reserved_quantity = Decimal("0")

    reservation.status = ReservationStatus.RELEASED
    reservation.released_at = datetime.now(timezone.utc)

    db.add(
        InventoryTransaction(
            organisation_id=organisation_id,
            inventory_item_id=item.id,
            transaction_type=InventoryTransactionType.RELEASE,
            quantity=reservation.quantity,
            reference_type="RESERVATION",
            reference_id=reservation.id,
            notes="Reservation released",
            created_by=user.id,
        )
    )
    await db.flush()
    return reservation


def to_inventory_item_response_data(item: InventoryItem) -> dict:
    available = item.available_quantity
    product_name = item.product.name if item.product else None
    return {
        "id": item.id,
        "organisation_id": item.organisation_id,
        "product_id": item.product_id,
        "sku": item.sku,
        "current_quantity": item.current_quantity,
        "reserved_quantity": item.reserved_quantity,
        "available_quantity": available,
        "reorder_level": item.reorder_level,
        "unit_of_measure": item.unit_of_measure,
        "product_name": product_name,
        "is_low_stock": available <= item.reorder_level,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
