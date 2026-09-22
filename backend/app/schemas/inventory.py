"""
Tradeloop — Inventory Pydantic Schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.deal import DealState
from app.models.inventory import (
    AvailabilityStatus,
    InventoryTransactionType,
    ReservationStatus,
)


class InventoryItemCreate(BaseModel):
    product_id: uuid.UUID
    initial_quantity: Decimal = Field(default=Decimal("0.00"), ge=0)
    reorder_level: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: Optional[str] = Field(None, max_length=500)


class InventoryItemUpdate(BaseModel):
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    unit_of_measure: Optional[str] = Field(None, max_length=50)


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    current_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    reorder_level: Decimal
    unit_of_measure: str
    product_name: Optional[str] = None
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime


class InventoryAdjustRequest(BaseModel):
    """Adjust stock for a product. Positive = receipt, negative = write-down."""

    product_id: uuid.UUID
    quantity_delta: Decimal = Field(
        ...,
        description="Signed quantity change. +5000 adds stock; -100 reduces stock.",
    )
    notes: Optional[str] = Field(None, max_length=500)
    reorder_level: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode="after")
    def quantity_not_zero(self) -> "InventoryAdjustRequest":
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta must not be zero")
        return self


class AvailabilityRequest(BaseModel):
    requested_quantity: Decimal = Field(..., gt=0)


class AvailabilityResponse(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: Optional[str] = None
    requested_quantity: Decimal
    current_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    shortfall: Decimal
    status: AvailabilityStatus
    unit_of_measure: str
    message: str


class ReserveRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0)
    deal_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    inventory_item_id: uuid.UUID
    deal_id: Optional[uuid.UUID] = None
    quantity: Decimal
    status: ReservationStatus
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    released_at: Optional[datetime] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None


class InventoryTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    inventory_item_id: uuid.UUID
    transaction_type: InventoryTransactionType
    quantity: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    sku: Optional[str] = None
    product_name: Optional[str] = None


class DealAvailabilityLine(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    requested_quantity: Decimal
    current_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    shortfall: Decimal
    status: AvailabilityStatus
    unit_of_measure: str
    message: str


class DealAvailabilityResponse(BaseModel):
    deal_id: uuid.UUID
    reference: str
    buyer_name: str
    overall_status: AvailabilityStatus
    lines: List[DealAvailabilityLine]


class DispatchItemDetail(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    quantity: Decimal
    unit_of_measure: str
    description: Optional[str] = None


class DealDispatchHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deal_id: uuid.UUID
    reference: str
    buyer_name: str
    state: DealState
    items_sent: List[DispatchItemDetail]
    incoterm: Optional[str] = None
    incoterm_place: Optional[str] = None
    total_amount: Optional[Decimal] = None
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
