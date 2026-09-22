"""
Tradeloop — Deal Pydantic Schemas (Phase 3, 4, 7, 8)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

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


class DealTransitionRequest(BaseModel):
    target_state: DealState
    reason: Optional[str] = Field(None, max_length=500)
    details: Optional[Dict[str, Any]] = None


class ShortfallAction(str, enum.Enum):
    REDUCE_TO_AVAILABLE = "REDUCE_TO_AVAILABLE"
    ACCEPT_FOR_PRODUCTION = "ACCEPT_FOR_PRODUCTION"


class ShortfallResolveRequest(BaseModel):
    product_id: uuid.UUID
    action: ShortfallAction
    custom_quantity: Optional[Decimal] = None
    notes: Optional[str] = None


class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
