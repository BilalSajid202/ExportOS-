"""
Tradeloop — Document Generation & Consistency Schemas (Phases 10 & 11)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.documents import DocumentStatus, DocumentType


class GeneratedDocumentResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    document_set_id: uuid.UUID
    doc_type: DocumentType
    document_number: str
    title: str
    content_json: Dict[str, Any]
    sha256_hash: str
    status: DocumentStatus
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentSetResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    revision_number: int
    status: DocumentStatus
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    documents: List[GeneratedDocumentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentGenerateRequest(BaseModel):
    notes: Optional[str] = None
    override_port_of_loading: Optional[str] = "Karachi Port (PKBQM/PKKHI)"
    payment_terms: Optional[str] = "100% LC at sight"


class ConsistencyCheckItem(BaseModel):
    check_name: str
    field: str
    is_valid: bool
    message: str
    documents_compared: List[str]
    values: Dict[str, Any]


class ConsistencyCheckResponse(BaseModel):
    deal_id: uuid.UUID
    revision_number: int
    is_consistent: bool
    score: int  # 0 to 100
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[ConsistencyCheckItem]
    discrepancies: List[str]
    summary_message: str
