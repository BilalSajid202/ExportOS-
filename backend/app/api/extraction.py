"""
ExportOS — AI Extraction & Human Review API

Endpoints:
  - POST /api/deals/{deal_id}/extract          - Run AI extraction on deal inquiry
  - GET  /api/deals/{deal_id}/extraction       - Retrieve latest extraction result
  - POST /api/deals/{deal_id}/extraction/confirm - Confirm/edit extracted fields & update deal
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.artifact import Artifact
from app.models.deal import Deal, DealLineItem
from app.models.extraction import ExtractionResult, ExtractionStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.extraction import (
    ExtractionConfirmPayload,
    ExtractionResponse,
)
from app.services.ai_extractor import AIExtractionService

router = APIRouter(prefix="/deals", tags=["AI Extraction"])


@router.post(
    "/{deal_id}/extract",
    response_model=ExtractionResponse,
    summary="Run AI interpretation & extraction on a deal's inquiry",
)
async def run_deal_extraction(
    deal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResponse:
    """
    Executes AI extraction:
      1. Reads raw customer message from linked artifact or deal notes
      2. Interprets commercial fields (product, quantity, Incoterm, destination port, price)
      3. Calculates confidence scores and extracts verbatim evidence quotes
      4. Persists ExtractionResult in PENDING_REVIEW status
    """
    # 1. Fetch deal with tenant check
    deal_query = (
        select(Deal)
        .options(selectinload(Deal.reservations), selectinload(Deal.line_items))
        .where(
            Deal.id == deal_id,
            Deal.organisation_id == current_user.organisation_id,
        )
    )
    deal_res = await db.execute(deal_query)
    deal = deal_res.scalar_one_or_none()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # 2. Find linked raw content or notes
    raw_text = ""
    artifact_id = None

    artifact_query = (
        select(Artifact)
        .where(
            Artifact.deal_id == deal.id,
            Artifact.organisation_id == current_user.organisation_id,
        )
        .order_by(Artifact.created_at.desc())
    )
    art_res = await db.execute(artifact_query)
    artifact = art_res.scalar_one_or_none()

    if artifact:
        artifact_id = artifact.id
        if artifact.raw_content:
            raw_text = artifact.raw_content
        elif artifact.subject:
            raw_text = f"{artifact.subject}. {deal.notes or ''}"

    if not raw_text and deal.notes:
        raw_text = deal.notes

    if not raw_text:
        raw_text = f"Inquiry from {deal.buyer_name} for export goods."

    # 3. Run AI extraction engine
    extracted_data = await AIExtractionService.extract_from_text(raw_text)

    # 4. Check if extraction result already exists for this deal
    existing_ext_query = (
        select(ExtractionResult)
        .where(
            ExtractionResult.deal_id == deal.id,
            ExtractionResult.organisation_id == current_user.organisation_id,
        )
        .order_by(ExtractionResult.created_at.desc())
    )
    existing_res = await db.execute(existing_ext_query)
    extraction_record = existing_res.scalar_one_or_none()

    if extraction_record:
        extraction_record.extracted_data = extracted_data
        extraction_record.artifact_id = artifact_id
        extraction_record.status = ExtractionStatus.PENDING_REVIEW
        extraction_record.model_name = "exportos-ai-extractor-v1"
        extraction_record.model_version = "1.1"
        extraction_record.reviewed_by = None
        extraction_record.reviewed_at = None
    else:
        extraction_record = ExtractionResult(
            organisation_id=current_user.organisation_id,
            deal_id=deal.id,
            artifact_id=artifact_id,
            model_name="exportos-ai-extractor-v1",
            model_version="1.1",
            extracted_data=extracted_data,
            status=ExtractionStatus.PENDING_REVIEW,
        )
        db.add(extraction_record)

    await db.commit()
    await db.refresh(extraction_record)
    return ExtractionResponse.model_validate(extraction_record)


@router.get(
    "/{deal_id}/extraction",
    response_model=ExtractionResponse,
    summary="Get latest AI extraction result for a deal",
)
async def get_deal_extraction(
    deal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResponse:
    """Retrieves the latest structured extraction result and field review state."""
    query = (
        select(ExtractionResult)
        .where(
            ExtractionResult.deal_id == deal_id,
            ExtractionResult.organisation_id == current_user.organisation_id,
        )
        .order_by(ExtractionResult.created_at.desc())
    )
    res = await db.execute(query)
    extraction = res.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extraction found for this deal. Run POST /deals/{id}/extract first.",
        )

    return ExtractionResponse.model_validate(extraction)


@router.post(
    "/{deal_id}/extraction/confirm",
    response_model=ExtractionResponse,
    summary="Confirm & apply human-reviewed extraction values to the deal",
)
async def confirm_deal_extraction(
    deal_id: uuid.UUID,
    payload: ExtractionConfirmPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResponse:
    """
    Human Review Confirmation Gateway:
      1. Updates field-level confirmation statuses and overrides
      2. If auto_create_line_item is True, matches or creates Product and adds DealLineItem
      3. Marks extraction as CONFIRMED or EDITED with reviewer audit stamp
    """
    # 1. Fetch deal
    deal_query = (
        select(Deal)
        .options(selectinload(Deal.line_items))
        .where(
            Deal.id == deal_id,
            Deal.organisation_id == current_user.organisation_id,
        )
    )
    deal_res = await db.execute(deal_query)
    deal = deal_res.scalar_one_or_none()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # 2. Fetch extraction result
    ext_query = (
        select(ExtractionResult)
        .where(
            ExtractionResult.deal_id == deal.id,
            ExtractionResult.organisation_id == current_user.organisation_id,
        )
        .order_by(ExtractionResult.created_at.desc())
    )
    ext_res = await db.execute(ext_query)
    extraction = ext_res.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction result not found. Run extract first.",
        )

    # 3. Update field values from confirmation payload
    has_edits = False
    current_data = dict(extraction.extracted_data or {})

    for field_name, field_confirm in payload.fields.items():
        if field_name in current_data:
            orig_val = current_data[field_name].get("value")
            new_val = field_confirm.value
            if str(orig_val) != str(new_val):
                has_edits = True
            current_data[field_name]["value"] = new_val
            current_data[field_name]["confirmation_status"] = field_confirm.confirmation_status
        else:
            current_data[field_name] = {
                "value": field_confirm.value,
                "confidence": 1.0,
                "evidence": "Human specified",
                "source_reference": "user_input",
                "confirmation_status": field_confirm.confirmation_status,
            }

    extraction.extracted_data = current_data
    extraction.status = ExtractionStatus.EDITED if has_edits else ExtractionStatus.CONFIRMED
    extraction.reviewed_by = current_user.id
    extraction.reviewed_at = datetime.now(timezone.utc)

    # 4. Create/update Deal Line Item if requested
    if payload.auto_create_line_item:
        product_name = current_data.get("product_name", {}).get("value")
        qty_val = current_data.get("quantity", {}).get("value")
        uom_val = current_data.get("uom", {}).get("value") or "PCS"

        if product_name and qty_val:
            try:
                qty_decimal = Decimal(str(qty_val))
            except Exception:
                qty_decimal = Decimal("1000")

            matched_product = None

            # Check if user provided explicit product_id
            if payload.product_id:
                prod_q = select(Product).where(
                    Product.id == payload.product_id,
                    Product.organisation_id == current_user.organisation_id,
                )
                prod_res = await db.execute(prod_q)
                matched_product = prod_res.scalar_one_or_none()

            # Otherwise match by product name or SKU
            if not matched_product:
                prod_q = select(Product).where(
                    Product.organisation_id == current_user.organisation_id,
                    Product.name.ilike(f"%{product_name}%"),
                )
                prod_res = await db.execute(prod_q)
                matched_product = prod_res.scalar_one_or_none()

            # If no product exists in catalogue, auto-create a standard product entry
            if not matched_product:
                clean_sku = "".join(c for c in product_name.upper() if c.isalnum())[:8] or "PROD"
                sku_candidate = f"SKU-{clean_sku}-001"
                matched_product = Product(
                    organisation_id=current_user.organisation_id,
                    sku=sku_candidate,
                    name=str(product_name),
                    description=f"Auto-catalogued from inquiry extraction: {product_name}",
                    unit_of_measure=str(uom_val),
                    selling_currency="USD",
                    weight_kg=Decimal("0.450"),
                    carton_capacity=20,
                    is_active=True,
                )
                db.add(matched_product)
                await db.flush()

            # Add or update line item on deal
            if not deal.line_items:
                line_item = DealLineItem(
                    organisation_id=current_user.organisation_id,
                    deal_id=deal.id,
                    product_id=matched_product.id,
                    quantity=qty_decimal,
                    description=f"Confirmed line item: {product_name}",
                )
                db.add(line_item)
            else:
                deal.line_items[0].product_id = matched_product.id
                deal.line_items[0].quantity = qty_decimal
                deal.line_items[0].description = f"Confirmed line item: {product_name}"

    await db.commit()
    await db.refresh(extraction)
    return ExtractionResponse.model_validate(extraction)
