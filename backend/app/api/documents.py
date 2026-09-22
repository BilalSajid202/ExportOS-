"""
Tradeloop — Multi-Document Generation & Consistency Checker API (Phases 10 & 11)

Endpoints:
  - POST /deals/{deal_id}/documents/generate       - Generate complete export document set (PI, CI, PL, CoO)
  - GET  /deals/{deal_id}/documents                - Retrieve active document set and documents
  - GET  /deals/{deal_id}/documents/consistency-check - Run deterministic cross-document audit
  - GET  /documents/{document_id}                  - Get generated document JSON
  - GET  /documents/{document_id}/html             - Get printable HTML preview
  - POST /documents/{document_id}/approve          - Approve export document
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.deal import Deal, DealLineItem, DealState
from app.models.documents import (
    DocumentSet,
    DocumentStatus,
    DocumentType,
    GeneratedDocument,
)
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.schemas.documents import (
    ConsistencyCheckResponse,
    DocumentGenerateRequest,
    DocumentSetResponse,
    GeneratedDocumentResponse,
)
from app.services import consistency_checker as consistency_service
from app.services import deal_state as deal_state_service
from app.services import document_generator as doc_gen_service

router = APIRouter(tags=["Export Documents"])

_DOC_MANAGERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.DOCUMENTATION_OFFICER,
)


@router.post(
    "/deals/{deal_id}/documents/generate",
    response_model=DocumentSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate complete set of export documents for a deal",
)
async def generate_deal_documents(
    deal_id: uuid.UUID,
    payload: DocumentGenerateRequest,
    current_user: User = Depends(_DOC_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> DocumentSetResponse:
    # 1. Fetch deal with products
    deal_q = (
        select(Deal)
        .options(selectinload(Deal.line_items).selectinload(DealLineItem.product))
        .where(
            Deal.id == deal_id,
            Deal.organisation_id == current_user.organisation_id,
        )
    )
    deal_res = await db.execute(deal_q)
    deal = deal_res.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    if not deal.line_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deal has no line items. Add products before generating documents.",
        )

    # 2. Fetch organisation
    org_res = await db.execute(
        select(Organisation).where(Organisation.id == current_user.organisation_id)
    )
    organisation = org_res.scalar_one()

    # 3. Generate document set
    doc_set = await doc_gen_service.generate_deal_document_set(
        db=db,
        deal=deal,
        organisation=organisation,
        notes=payload.notes,
        override_port_of_loading=payload.override_port_of_loading or "Karachi Port (PKBQM/PKKHI), Pakistan",
        payment_terms=payload.payment_terms or "100% LC at sight",
    )

    # 4. Advance deal to DOCS_READY if in CONFIRMED or IN_PRODUCTION
    if deal.state in (DealState.CONFIRMED, DealState.IN_PRODUCTION):
        await deal_state_service.transition_deal_state(
            db=db,
            deal=deal,
            target_state=DealState.DOCS_READY,
            user=current_user,
            reason=f"Generated export document set (Revision #{doc_set.revision_number})",
            extra_details={"document_set_id": str(doc_set.id)},
        )
    else:
        await deal_state_service.record_audit_entry(
            db=db,
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            user=current_user,
            action="DOCUMENTS_GENERATED",
            from_state=deal.state.value,
            to_state=deal.state.value,
            details={"document_set_id": str(doc_set.id), "revision": doc_set.revision_number},
            notes=f"Generated export document set #{doc_set.revision_number}",
        )
        await db.commit()

    # Refetch with loaded documents
    res = await db.execute(
        select(DocumentSet)
        .options(selectinload(DocumentSet.documents))
        .where(DocumentSet.id == doc_set.id)
    )
    loaded_set = res.scalar_one()
    return DocumentSetResponse.model_validate(loaded_set)


@router.get(
    "/deals/{deal_id}/documents",
    response_model=Optional[DocumentSetResponse],
    summary="Get active document set for a deal",
)
async def get_deal_documents(
    deal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[DocumentSetResponse]:
    res = await db.execute(
        select(DocumentSet)
        .options(selectinload(DocumentSet.documents))
        .where(
            DocumentSet.deal_id == deal_id,
            DocumentSet.organisation_id == current_user.organisation_id,
            DocumentSet.is_active == True,
        )
        .order_by(DocumentSet.revision_number.desc())
    )
    doc_set = res.scalars().first()
    if not doc_set:
        return None
    return DocumentSetResponse.model_validate(doc_set)


@router.get(
    "/deals/{deal_id}/documents/consistency-check",
    response_model=ConsistencyCheckResponse,
    summary="Run cross-document consistency audit on latest documents",
)
async def get_deal_documents_consistency(
    deal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsistencyCheckResponse:
    res = await db.execute(
        select(DocumentSet)
        .options(selectinload(DocumentSet.documents))
        .where(
            DocumentSet.deal_id == deal_id,
            DocumentSet.organisation_id == current_user.organisation_id,
            DocumentSet.is_active == True,
        )
        .order_by(DocumentSet.revision_number.desc())
    )
    doc_set = res.scalars().first()
    if not doc_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents generated yet. Click 'Generate Export Documents' first.",
        )

    return consistency_service.check_document_set_consistency(doc_set)


@router.get(
    "/documents/{document_id}",
    response_model=GeneratedDocumentResponse,
    summary="Get individual generated document",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedDocumentResponse:
    res = await db.execute(
        select(GeneratedDocument).where(
            GeneratedDocument.id == document_id,
            GeneratedDocument.organisation_id == current_user.organisation_id,
        )
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return GeneratedDocumentResponse.model_validate(doc)


@router.get(
    "/documents/{document_id}/html",
    response_class=Response,
    summary="Get rendered printable HTML for export document",
)
async def get_document_html(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(GeneratedDocument).where(
            GeneratedDocument.id == document_id,
            GeneratedDocument.organisation_id == current_user.organisation_id,
        )
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    html_content = doc_gen_service.render_document_html(doc)
    return Response(content=html_content, media_type="text/html")


@router.post(
    "/documents/{document_id}/approve",
    response_model=GeneratedDocumentResponse,
    summary="Approve export document",
)
async def approve_document(
    document_id: uuid.UUID,
    current_user: User = Depends(_DOC_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> GeneratedDocumentResponse:
    res = await db.execute(
        select(GeneratedDocument).where(
            GeneratedDocument.id == document_id,
            GeneratedDocument.organisation_id == current_user.organisation_id,
        )
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.status = DocumentStatus.APPROVED
    doc.approved_by = current_user.id
    doc.approved_at = datetime.now(timezone.utc)
    db.add(doc)

    await deal_state_service.record_audit_entry(
        db=db,
        organisation_id=current_user.organisation_id,
        deal_id=doc.deal_id,
        user=current_user,
        action="DOCUMENT_APPROVED",
        from_state=None,
        to_state=None,
        details={"doc_type": doc.doc_type.value, "document_number": doc.document_number},
        notes=f"Approved export document: {doc.title}",
    )
    await db.commit()
    await db.refresh(doc)
    return GeneratedDocumentResponse.model_validate(doc)
