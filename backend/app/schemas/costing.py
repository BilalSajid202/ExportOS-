"""
Tradeloop — Costing & Quotation Schemas (Phase 8)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.costing import CostComponentType, Incoterm, QuoteStatus


# ── Cost Component Schemas ─────────────────────────────────────

class CostComponentCreate(BaseModel):
    cost_type: CostComponentType
    description: str = Field(..., max_length=255)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    notes: Optional[str] = None


class CostComponentResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    cost_type: CostComponentType
    description: str
    amount: Decimal
    currency: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Quote Schemas ──────────────────────────────────────────────

class QuoteCalculateRequest(BaseModel):
    incoterm: Incoterm
    incoterm_place: str = Field(..., max_length=255)
    currency: str = Field(default="USD", max_length=3)
    margin_percentage: Decimal = Field(default=Decimal("15.00"), ge=0, le=100)
    notes: Optional[str] = None


class QuoteApproveRequest(BaseModel):
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    incoterm: Incoterm
    incoterm_place: str
    currency: str
    base_cost: Decimal
    logistics_cost: Decimal
    total_cost: Decimal
    margin_percentage: Decimal
    margin_amount: Decimal
    total_quote_price: Decimal
    unit_price: Decimal
    status: QuoteStatus
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealCostingSummaryResponse(BaseModel):
    deal_id: uuid.UUID
    components: List[CostComponentResponse]
    total_components_cost: Decimal
    active_quote: Optional[QuoteResponse]
    quotes_history: List[QuoteResponse]
