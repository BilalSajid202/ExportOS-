"""
Tradeloop — AI Extraction Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.extraction import ExtractionStatus


class ExtractedFieldItem(BaseModel):
    """Metadata container for an individual extracted attribute."""
    value: Any = None
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from inquiry")
    source_reference: Optional[str] = Field(None, description="Location in source document or field")
    confirmation_status: str = Field("PENDING", description="PENDING | CONFIRMED | EDITED | REJECTED")


class ExtractionDataSchema(BaseModel):
    """Full structured extraction dictionary."""
    product_name: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    quantity: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    uom: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    destination_port: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    incoterm: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    incoterm_place: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    target_price: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    currency: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    delivery_date: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    payment_terms: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)
    special_instructions: ExtractedFieldItem = Field(default_factory=ExtractedFieldItem)


class ExtractionResponse(BaseModel):
    """API response model for an extraction result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: uuid.UUID
    artifact_id: Optional[uuid.UUID]
    model_name: str
    model_version: str
    extracted_data: Dict[str, Any]
    status: ExtractionStatus
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ExtractionConfirmFieldPayload(BaseModel):
    """Override or confirmation value for a specific field."""
    value: Any
    confirmation_status: str = "CONFIRMED"


class ExtractionConfirmPayload(BaseModel):
    """Payload sent by user when reviewing & confirming AI extraction."""
    fields: Dict[str, ExtractionConfirmFieldPayload] = Field(..., description="Confirmed or edited field values")
    auto_create_line_item: bool = Field(True, description="Whether to add/update deal line item automatically")
    product_id: Optional[uuid.UUID] = Field(None, description="Matched catalogue product ID if selected")
