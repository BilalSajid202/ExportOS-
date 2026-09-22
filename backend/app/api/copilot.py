"""
Tradeloop — Export Copilot & Vector Database API Endpoints (Phase 14)
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    DealReadinessResponse,
    BuyerMessageDraftRequest,
    BuyerMessageDraftResponse,
    VectorStatusResponse,
)
from app.services.copilot import (
    ask_export_copilot,
    inspect_deal_readiness,
    draft_buyer_correspondence,
)
from app.services.vector_pipeline import (
    sync_docs_folder_to_qdrant,
    sync_deal_to_qdrant,
    get_qdrant_client,
    COLLECTION_NAME,
)

router = APIRouter(prefix="/copilot", tags=["Export Copilot & Vector RAG"])


@router.post("/query", response_model=CopilotQueryResponse)
async def query_copilot(
    payload: CopilotQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Conversational RAG endpoint combining Qdrant semantic vector search,
    live SQL deal records, and Qwen 2.5 with zero-hallucination guardrails.
    """
    return await ask_export_copilot(
        query=payload.query,
        deal_id=payload.deal_id,
        organisation_id=current_user.organisation_id,
        db=db,
        top_k=payload.top_k or 5,
    )


@router.get("/deals/{deal_id}/readiness", response_model=DealReadinessResponse)
async def get_deal_readiness(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    7-Pillar 'Ready-to-Ship' deterministic inspection engine.
    """
    try:
        return await inspect_deal_readiness(deal_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/deals/{deal_id}/draft-message", response_model=BuyerMessageDraftResponse)
async def generate_buyer_draft(
    deal_id: UUID,
    payload: BuyerMessageDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER, UserRole.SALES, UserRole.DOCUMENTATION_OFFICER)
    ),
):
    """
    Generate commercial buyer correspondence draft with Human-in-the-loop Gate (FR-COP-05).
    """
    try:
        return await draft_buyer_correspondence(
            template_type=payload.template_type,
            deal_id=deal_id,
            organisation_id=current_user.organisation_id,
            db=db,
            custom_notes=payload.custom_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/sync-docs")
def sync_docs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER)
    ),
):
    """
    Re-indexes all markdown reference documents in backend/data/docs/ into Qdrant.
    """
    chunks_count = sync_docs_folder_to_qdrant()
    return {"message": "Docs synchronized to Qdrant successfully", "chunks_indexed": chunks_count}


@router.post("/deals/{deal_id}/sync-vector")
async def sync_deal_vector(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-indexes a deal's latest database records into Qdrant vectors.
    """
    chunks_count = await sync_deal_to_qdrant(deal_id, current_user.organisation_id, db)
    return {"message": "Deal synchronized to Qdrant", "chunks_indexed": chunks_count}


@router.get("/vector-status", response_model=VectorStatusResponse)
def get_vector_status(
    current_user: User = Depends(get_current_user),
):
    """
    Checks Qdrant vector database collection status and indexed chunk metrics.
    """
    client = get_qdrant_client()
    try:
        count_res = client.count(collection_name=COLLECTION_NAME)
        total_chunks = count_res.count
        is_conn = True
    except Exception:
        total_chunks = 0
        is_conn = False

    return VectorStatusResponse(
        collection_name=COLLECTION_NAME,
        total_indexed_chunks=total_chunks,
        is_connected=is_conn,
        storage_type="Qdrant Embedded / Cloud",
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )
