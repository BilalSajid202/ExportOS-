"""
ExportOS — Compliance & HS Code Advisory API Routes

Endpoints:
  - GET  /compliance/deals/{deal_id}           - Get deal compliance summary & checklist
  - POST /compliance/deals/{deal_id}/regenerate - Re-evaluate rules against current deal revision
  - PUT  /compliance/deals/{deal_id}/checks/{check_id} - Update check item status & evidence
  - POST /compliance/deals/{deal_id}/hs-suggest - Get AI HS code classification suggestions
  - POST /compliance/deals/{deal_id}/hs-confirm - Human confirmation gate & product catalogue sync
  - POST /compliance/regulations/query        - Grounded SBP & export trade regulation advisory
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.compliance import (
    ComplianceCheckResponse,
    ComplianceCheckUpdate,
    ComplianceSummaryResponse,
    HSConfirmRequest,
    HSSuggestionRequest,
    HSSuggestionResponse,
    RegulationQueryRequest,
    RegulationQueryResponse,
)
from app.services import compliance as compliance_service
from app.services import hs_advisor as hs_service
from app.services import sbp_regulations as sbp_service

router = APIRouter(prefix="/compliance", tags=["Compliance & Regulations"])

_COMPLIANCE_WRITERS = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.DOCUMENTATION_OFFICER,
)


@router.get(
    "/deals/{deal_id}",
    response_model=ComplianceSummaryResponse,
    summary="Get compliance summary and checklist for a deal",
)
async def get_deal_compliance(
    deal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplianceSummaryResponse:
    try:
        data = await compliance_service.compute_compliance_summary(
            db, current_user.organisation_id, deal_id
        )
        await db.commit()
        return ComplianceSummaryResponse(**data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/deals/{deal_id}/regenerate",
    response_model=ComplianceSummaryResponse,
    summary="Re-evaluate and refresh compliance checklist against current deal terms",
)
async def regenerate_deal_compliance(
    deal_id: uuid.UUID,
    current_user: User = Depends(_COMPLIANCE_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ComplianceSummaryResponse:
    try:
        await compliance_service.ensure_deal_compliance_checks(
            db, current_user.organisation_id, deal_id, force_regenerate=True
        )
        data = await compliance_service.compute_compliance_summary(
            db, current_user.organisation_id, deal_id
        )
        await db.commit()
        return ComplianceSummaryResponse(**data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put(
    "/deals/{deal_id}/checks/{check_id}",
    response_model=ComplianceCheckResponse,
    summary="Update compliance check status and evidence",
)
async def update_check_status(
    deal_id: uuid.UUID,
    check_id: uuid.UUID,
    payload: ComplianceCheckUpdate,
    current_user: User = Depends(_COMPLIANCE_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> ComplianceCheckResponse:
    try:
        check = await compliance_service.update_compliance_check(
            db,
            organisation_id=current_user.organisation_id,
            check_id=check_id,
            status=payload.status,
            notes=payload.notes,
            evidence_ref=payload.evidence_ref,
            user=current_user,
        )
        await db.commit()
        await db.refresh(check)
        return ComplianceCheckResponse.model_validate(check)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/deals/{deal_id}/hs-suggest",
    response_model=HSSuggestionResponse,
    summary="Get AI HS code classification suggestion with GRI reasoning",
)
async def suggest_hs_code(
    deal_id: uuid.UUID,
    payload: HSSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HSSuggestionResponse:
    data = await hs_service.suggest_hs_code_for_product(
        db,
        organisation_id=current_user.organisation_id,
        product_id=payload.product_id,
        deal_id=deal_id,
        product_name=payload.product_name,
        description=payload.description,
        specifications=payload.specifications,
    )
    await db.commit()
    return HSSuggestionResponse(**data)


@router.post(
    "/deals/{deal_id}/hs-confirm",
    response_model=HSSuggestionResponse,
    summary="Confirm HS Code for deal and sync to Product Master Catalogue",
)
async def confirm_hs_code_endpoint(
    deal_id: uuid.UUID,
    payload: HSConfirmRequest,
    current_user: User = Depends(_COMPLIANCE_WRITERS),
    db: AsyncSession = Depends(get_db),
) -> HSSuggestionResponse:
    record = await hs_service.confirm_hs_code(
        db,
        organisation_id=current_user.organisation_id,
        confirmed_code=payload.confirmed_code,
        deal_id=deal_id,
        product_id=payload.product_id,
        update_catalogue=payload.update_catalogue,
        user=current_user,
    )
    await db.commit()
    await db.refresh(record)

    tax_entry = hs_service.match_pct_taxonomy(payload.confirmed_code)
    rebate = tax_entry.get("rebate") if tax_entry else "Standard Export Refinance Eligible"

    return HSSuggestionResponse(
        id=record.id,
        product_id=record.product_id,
        deal_id=record.deal_id,
        suggested_code=record.suggested_code,
        confirmed_code=record.confirmed_code,
        heading_title=record.heading_title,
        reasoning=record.reasoning,
        confidence=record.confidence,
        tariff_source=record.tariff_source,
        status=record.status,
        is_reused_from_catalogue=False,
        applicable_export_rebate=rebate,
    )


@router.post(
    "/regulations/query",
    response_model=RegulationQueryResponse,
    summary="Query grounded SBP and Pakistani trade compliance regulations",
)
async def query_regulations(
    payload: RegulationQueryRequest,
    current_user: User = Depends(get_current_user),
) -> RegulationQueryResponse:
    data = sbp_service.query_sbp_regulations(
        query_text=payload.query,
        destination_country=payload.destination_country,
        incoterm=payload.incoterm,
        payment_method=payload.payment_method,
    )
    return RegulationQueryResponse(**data)
