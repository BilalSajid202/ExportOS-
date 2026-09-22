"""
Tradeloop — Inquiry Ingestion & Inbound Artifacts API

Endpoints:
  - POST /api/inquiries/upload  - Upload RFQ documents (PDF, Excel, Word, Text)
  - POST /api/inquiries/text    - Ingest raw email or pasted text inquiry
  - GET  /api/inquiries         - List all inquiries and artifacts (tenant-isolated)
  - GET  /api/inquiries/{id}    - Get inquiry artifact details and linked deal
  - GET  /api/inquiries/{id}/download - Download the uploaded inquiry file
"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.artifact import Artifact, ArtifactType, InboundChannel
from app.models.deal import Deal, DealState
from app.models.user import User
from app.schemas.inquiry import (
    ArtifactResponse,
    InquiryDetailResponse,
    TextInputInquiryRequest,
)

router = APIRouter(prefix="/inquiries", tags=["Inquiries & Artifacts"])


def _generate_deal_reference(buyer_name: str) -> str:
    """Generate a clean deal reference like INQ-2026-XXXX."""
    timestamp_part = datetime.now(timezone.utc).strftime("%y%m%d")
    random_part = uuid.uuid4().hex[:4].upper()
    return f"INQ-{timestamp_part}-{random_part}"


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and special character issues."""
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\s.-]", "", filename).strip()
    return filename or "document"


def _format_artifact_response(artifact: Artifact) -> ArtifactResponse:
    """Helper to convert Artifact ORM model to ArtifactResponse schema."""
    resp = ArtifactResponse.model_validate(artifact)
    if artifact.deal:
        resp.deal_reference = artifact.deal.reference
        resp.deal_buyer_name = artifact.deal.buyer_name
        resp.deal_state = artifact.deal.state.value if hasattr(artifact.deal.state, "value") else str(artifact.deal.state)
    return resp


@router.post(
    "/upload",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload buyer inquiry document (PDF, Excel, Word, Text)",
)
async def upload_inquiry_file(
    file: UploadFile = File(..., description="Inquiry document file"),
    buyer_name: str = Form(..., min_length=2, max_length=255, description="Buyer or company name"),
    sender_email: Optional[str] = Form(None, description="Sender email address"),
    subject: Optional[str] = Form(None, description="Subject line or RFQ reference"),
    notes: Optional[str] = Form(None, description="Optional notes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """
    Ingests an inbound document:
      1. Reads stream and calculates cryptographic SHA-256 hash
      2. Persists file to tenant-isolated upload directory
      3. Creates immutable Artifact record
      4. Automatically creates an initial Deal in INQUIRY state
    """
    settings = get_settings()

    # Read file content into memory to compute hash
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    sha256_hash = hashlib.sha256(content).hexdigest()

    # Ensure tenant directory exists
    org_upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.organisation_id))
    os.makedirs(org_upload_dir, exist_ok=True)

    safe_name = _sanitize_filename(file.filename or "inquiry_document")
    timestamp_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp_prefix}_{safe_name}"
    file_path = os.path.join(org_upload_dir, saved_filename)

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Create Initial Deal in INQUIRY state
    deal_ref = _generate_deal_reference(buyer_name)
    deal = Deal(
        organisation_id=current_user.organisation_id,
        reference=deal_ref,
        buyer_name=buyer_name,
        state=DealState.INQUIRY,
        notes=f"Inquiry received via file upload: {safe_name}. {notes or ''}".strip(),
        created_by=current_user.id,
    )
    db.add(deal)
    await db.flush()  # Populates deal.id

    # Create Artifact record
    artifact = Artifact(
        organisation_id=current_user.organisation_id,
        deal_id=deal.id,
        artifact_type=ArtifactType.INBOUND_INQUIRY,
        channel=InboundChannel.FILE_UPLOAD,
        filename=safe_name,
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=file_size,
        file_path=file_path,
        sha256_hash=sha256_hash,
        raw_content=None,
        sender_info=sender_email or buyer_name,
        subject=subject or f"RFQ from {buyer_name}",
        created_by=current_user.id,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    await db.refresh(deal)

    artifact.deal = deal
    return _format_artifact_response(artifact)


@router.post(
    "/text",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw email or pasted text inquiry",
)
async def ingest_text_inquiry(
    payload: TextInputInquiryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """
    Ingests raw email or pasted inquiry text:
      1. Computes cryptographic SHA-256 hash of the content
      2. Creates immutable Artifact record
      3. Automatically creates an initial Deal in INQUIRY state
    """
    raw_bytes = payload.raw_content.encode("utf-8")
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
    file_size = len(raw_bytes)

    # Create Initial Deal in INQUIRY state
    deal_ref = _generate_deal_reference(payload.buyer_name)
    deal = Deal(
        organisation_id=current_user.organisation_id,
        reference=deal_ref,
        buyer_name=payload.buyer_name,
        state=DealState.INQUIRY,
        notes=f"Inquiry ingested from text/email. {payload.notes or ''}".strip(),
        created_by=current_user.id,
    )
    db.add(deal)
    await db.flush()  # Populates deal.id

    # Determine channel
    channel = InboundChannel.EMAIL if payload.sender_email else InboundChannel.WEB_FORM
    subject_title = payload.subject or f"Inquiry from {payload.buyer_name}"

    artifact = Artifact(
        organisation_id=current_user.organisation_id,
        deal_id=deal.id,
        artifact_type=ArtifactType.INBOUND_INQUIRY,
        channel=channel,
        filename=f"inquiry_{deal_ref}.txt",
        mime_type="text/plain",
        file_size_bytes=file_size,
        file_path=None,
        sha256_hash=sha256_hash,
        raw_content=payload.raw_content,
        sender_info=payload.sender_email or payload.buyer_name,
        subject=subject_title,
        created_by=current_user.id,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    await db.refresh(deal)

    artifact.deal = deal
    return _format_artifact_response(artifact)


@router.get(
    "",
    response_model=List[ArtifactResponse],
    summary="List all inbound inquiries and artifacts",
)
async def list_inquiries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ArtifactResponse]:
    """
    Lists all raw inquiries and artifacts for the caller's tenant organisation.
    Enforces strict tenant isolation.
    """
    query = (
        select(Artifact)
        .options(selectinload(Artifact.deal))
        .where(
            Artifact.organisation_id == current_user.organisation_id,
            Artifact.artifact_type == ArtifactType.INBOUND_INQUIRY,
        )
        .order_by(Artifact.created_at.desc())
    )
    result = await db.execute(query)
    artifacts = result.scalars().all()
    return [_format_artifact_response(a) for a in artifacts]


@router.get(
    "/{artifact_id}",
    response_model=InquiryDetailResponse,
    summary="Get inquiry artifact details",
)
async def get_inquiry(
    artifact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InquiryDetailResponse:
    """Retrieve full details of an inquiry artifact by ID."""
    query = (
        select(Artifact)
        .options(selectinload(Artifact.deal))
        .where(
            Artifact.id == artifact_id,
            Artifact.organisation_id == current_user.organisation_id,
        )
    )
    res = await db.execute(query)
    artifact = res.scalar_one_or_none()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry artifact not found",
        )

    return InquiryDetailResponse(
        artifact=_format_artifact_response(artifact),
        deal_id=artifact.deal_id,
        deal_reference=artifact.deal.reference if artifact.deal else None,
        deal_state=artifact.deal.state.value if artifact.deal and hasattr(artifact.deal.state, "value") else None,
    )


@router.get(
    "/{artifact_id}/download",
    summary="Download uploaded inquiry file",
)
async def download_inquiry_file(
    artifact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads the physical document file stored on disk for this artifact."""
    query = select(Artifact).where(
        Artifact.id == artifact_id,
        Artifact.organisation_id == current_user.organisation_id,
    )
    res = await db.execute(query)
    artifact = res.scalar_one_or_none()
    if not artifact or not artifact.file_path or not os.path.exists(artifact.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage",
        )

    return FileResponse(
        path=artifact.file_path,
        filename=artifact.filename,
        media_type=artifact.mime_type,
    )
