"""
ExportOS — Minimal Deal Pydantic Schemas (Phase 3)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.deal import DealState


class DealLineItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)


class DealCreateRequest(BaseModel):
    buyer_name: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None
    line_items: List[DealLineItemCreate] = Field(..., min_length=1)


class DealLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    description: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    reference: str
    buyer_name: str
    state: DealState
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    line_items: List[DealLineItemResponse] = []
