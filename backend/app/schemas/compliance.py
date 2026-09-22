"""
Tradeloop — Compliance & HS Code Classification Schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance import (
    ComplianceCategory,
    ComplianceStatus,
    HSClassificationStatus,
)


class ComplianceCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    rule_code: str
    category: ComplianceCategory
    title: str
    description: str
    authority: str
    status: ComplianceStatus
    is_mandatory: bool
    responsible_role: str
    notes: Optional[str] = None
    evidence_ref: Optional[str] = None
    completed_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ComplianceCheckUpdate(BaseModel):
    status: ComplianceStatus
    notes: Optional[str] = Field(None, max_length=1000)
    evidence_ref: Optional[str] = Field(None, max_length=255)


class ComplianceSummaryResponse(BaseModel):
    deal_id: uuid.UUID
    total_checks: int
    mandatory_total: int
    mandatory_completed: int
    mandatory_pending: int
    is_fully_compliant: bool
    completion_percentage: Decimal
    checks: List[ComplianceCheckResponse]


class HSSuggestionRequest(BaseModel):
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None


class HSSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    deal_id: Optional[uuid.UUID] = None
    suggested_code: str
    confirmed_code: Optional[str] = None
    heading_title: str
    reasoning: str
    confidence: Decimal
    tariff_source: str
    status: HSClassificationStatus
    is_reused_from_catalogue: bool = False
    applicable_export_rebate: Optional[str] = None


class HSConfirmRequest(BaseModel):
    confirmed_code: str = Field(..., min_length=4, max_length=20)
    product_id: Optional[uuid.UUID] = None
    update_catalogue: bool = True


class RegulationQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    deal_id: Optional[uuid.UUID] = None
    destination_country: Optional[str] = None
    incoterm: Optional[str] = None
    payment_method: Optional[str] = None


class RegulationCitation(BaseModel):
    source_title: str
    section_or_circular: str
    effective_date: str
    verbatim_text: str


class RegulationQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[RegulationCitation]
    authority: str
    effective_date: str
    last_verified: str
    disclaimer: str = (
        "Informational advisory only. Tradeloop provides regulatory guidance based on published SBP Foreign Exchange Manual and Pakistan Customs trade notices, but does not constitute official legal or customs clearance advice."
    )
