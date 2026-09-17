"""
ExportOS — Inquiry & Artifact Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.artifact import ArtifactType, InboundChannel
from app.schemas.auth import UserResponse


class TextInputInquiryRequest(BaseModel):
    """Payload for ingesting a raw email or text buyer inquiry."""
    buyer_name: str = Field(..., min_length=2, max_length=255, description="Buyer or company name")
    sender_email: Optional[str] = Field(None, max_length=255, description="Sender email address if known")
    subject: Optional[str] = Field(None, max_length=255, description="Inquiry or email subject line")
    raw_content: str = Field(..., min_length=5, description="Raw inquiry body or email content")
    notes: Optional[str] = Field(None, description="Optional internal notes")


class ArtifactResponse(BaseModel):
    """Artifact representation returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    deal_id: Optional[uuid.UUID]
    artifact_type: ArtifactType
    channel: InboundChannel
    filename: str
    mime_type: str
    file_size_bytes: int
    file_path: Optional[str]
    sha256_hash: str
    raw_content: Optional[str]
    sender_info: Optional[str]
    subject: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    deal_reference: Optional[str] = None
    deal_buyer_name: Optional[str] = None
    deal_state: Optional[str] = None


class InquiryDetailResponse(BaseModel):
    """Detailed inquiry response including raw content, hash, and linked deal summary."""
    artifact: ArtifactResponse
    deal_id: Optional[uuid.UUID]
    deal_reference: Optional[str]
    deal_state: Optional[str]
