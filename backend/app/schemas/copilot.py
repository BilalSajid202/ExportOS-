from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field


class RetrievedChunkInfo(BaseModel):
    id: str
    title: str
    text: str
    score: float
    source: str
    chunk_type: str
    is_global: bool = False


class ReadinessPillar(BaseModel):
    key: str
    name: str
    status: str  # PASSED, BLOCKED, WARNING, NOT_APPLICABLE
    message: str
    evidence: Optional[str] = None


class DealReadinessResponse(BaseModel):
    deal_id: UUID
    reference: str
    buyer_name: str
    overall_status: str  # READY_TO_SHIP, ACTION_REQUIRED, NOT_READY
    is_ready_to_ship: bool
    score_percentage: int
    pillars: List[ReadinessPillar]
    blockers: List[str]
    warnings: List[str]


class CopilotQueryRequest(BaseModel):
    query: str
    deal_id: Optional[UUID] = None
    top_k: Optional[int] = 5


class CopilotQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[str]
    retrieved_chunks: List[RetrievedChunkInfo] = Field(default_factory=list)
    readiness: Optional[DealReadinessResponse] = None
    suggested_followups: List[str] = Field(default_factory=list)


class BuyerMessageDraftRequest(BaseModel):
    template_type: str  # ORDER_CONFIRMATION, QUOTATION_LETTER, SHIPPING_ADVICE, PAYMENT_REMINDER_SBP, DISCREPANCY_NOTICE
    deal_id: UUID
    custom_notes: Optional[str] = None


class BuyerMessageDraftResponse(BaseModel):
    template_type: str
    subject: str
    body: str
    deal_reference: str
    buyer_name: str
    human_approval_required: bool = True


class VectorStatusResponse(BaseModel):
    collection_name: str
    total_indexed_chunks: int
    is_connected: bool
    storage_type: str
    last_synced_at: str
