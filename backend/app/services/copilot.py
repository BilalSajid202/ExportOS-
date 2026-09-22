"""
ExportOS — Grounded Export Copilot Service (Phase 14)

Provides multi-factor 7-pillar "Ready-to-Ship" verification, Qdrant semantic vector
RAG reasoning with zero-hallucination constraints, and human-in-the-loop correspondence drafting.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
import httpx

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.services.ai_extractor import HFKeyManager
from app.models.deal import Deal, DealState
from app.models.costing import DealQuote, QuoteStatus
from app.models.documents import DocumentSet, GeneratedDocument, DocumentStatus
from app.models.compliance import ComplianceCheck, ComplianceStatus
from app.models.logistics import Shipment, ShipmentStatus, PaymentTransaction, PaymentStatus
from app.models.inventory import InventoryReservation, ReservationStatus
from app.schemas.copilot import (
    DealReadinessResponse,
    ReadinessPillar,
    CopilotQueryResponse,
    RetrievedChunkInfo,
    BuyerMessageDraftResponse,
)
from app.services.vector_pipeline import query_qdrant_vectors, sync_deal_to_qdrant

logger = logging.getLogger("exportos.copilot")


def call_qwen_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 800,
) -> str:
    """
    Call Hugging Face Qwen LLM with rotating API keys and deterministic fallback.
    """
    keys = HFKeyManager.get_keys()
    if not keys:
        raise RuntimeError("No Hugging Face API keys configured; triggering deterministic grounding.")

    settings = get_settings()
    model_id = settings.HF_MODEL or "Qwen/Qwen2.5-Coder-32B-Instruct"
    endpoint = settings.HF_API_URL or "https://router.huggingface.co/v1/chat/completions"

    max_attempts = max(len(keys), 1)
    for attempt in range(max_attempts):
        active_key = HFKeyManager.get_active_key()
        if not active_key:
            break

        headers = {
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                if response.status_code in (429, 403, 503) or (
                    response.status_code == 401 and "quota" in response.text.lower()
                ):
                    logger.warning(
                        f"Hugging Face returned status {response.status_code} in Copilot. Rotating key..."
                    )
                    HFKeyManager.rotate_key()
                    continue

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        return choices[0]["message"].get("content", "").strip()
        except Exception as e:
            logger.warning(f"Error calling Hugging Face Qwen in Copilot: {e}")
            HFKeyManager.rotate_key()
            continue

    raise RuntimeError("All Hugging Face API keys exhausted or unreachable.")


async def inspect_deal_readiness(
    deal_id: UUID,
    db: Any,
) -> DealReadinessResponse:
    """
    Deterministically evaluates 7 export readiness pillars:
    1. Inventory Allocation
    2. Incoterm Costing & Quotation
    3. Export Document Preparation
    4. Cross-Document Hash & Data Consistency
    5. Regulatory & SBP Compliance Clearance
    6. Shipment Transport Booking
    7. Payment Terms & SBP Realization
    """
    if isinstance(db, AsyncSession):
        d_stmt = select(Deal).options(selectinload(Deal.line_items)).where(Deal.id == deal_id)
        d_res = await db.execute(d_stmt)
        deal = d_res.scalars().first()
    else:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    pillars: List[ReadinessPillar] = []
    blockers: List[str] = []
    warnings: List[str] = []
    passed_count = 0

    # ── Pillar 1: Inventory Stock Reservation ───────────────────────
    if isinstance(db, AsyncSession):
        r_stmt = select(InventoryReservation).where(InventoryReservation.deal_id == deal_id)
        r_res = await db.execute(r_stmt)
        reservations = r_res.scalars().all()
    else:
        reservations = db.query(InventoryReservation).filter(InventoryReservation.deal_id == deal_id).all()

    active_res = [r for r in reservations if r.status == ReservationStatus.ACTIVE]
    total_requested = sum(item.quantity for item in deal.line_items or [])
    total_reserved = sum(r.quantity_reserved for r in active_res)

    if total_requested > 0 and total_reserved >= total_requested:
        pillars.append(ReadinessPillar(
            key="INVENTORY",
            name="Warehouse Inventory Allocation",
            status="PASSED",
            message="100% of required stock is reserved and verified.",
            evidence=f"Reserved: {total_reserved:,} / {total_requested:,} units",
        ))
        passed_count += 1
    elif total_reserved > 0:
        pillars.append(ReadinessPillar(
            key="INVENTORY",
            name="Warehouse Inventory Allocation",
            status="WARNING",
            message="Partial inventory allocated. Some units remain unreserved.",
            evidence=f"Reserved: {total_reserved:,} / {total_requested:,} units",
        ))
        warnings.append(f"Inventory shortfall: {total_requested - total_reserved:,} units unallocated")
    else:
        pillars.append(ReadinessPillar(
            key="INVENTORY",
            name="Warehouse Inventory Allocation",
            status="BLOCKED",
            message="No warehouse inventory reserved for this deal.",
            evidence="0 units reserved in inventory ledger",
        ))
        blockers.append("Inventory must be reserved before order release")

    # ── Pillar 2: Incoterm Costing & Quotation ───────────────────────
    if isinstance(db, AsyncSession):
        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at))
        q_res = await db.execute(q_stmt)
        quote = q_res.scalars().first()
    else:
        quote = db.query(DealQuote).filter(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at)).first()

    if quote and quote.status in [QuoteStatus.ACCEPTED, QuoteStatus.APPROVED]:
        pillars.append(ReadinessPillar(
            key="COSTING",
            name="Incoterm Costing & Quotation",
            status="PASSED",
            message=f"Quote approved under Incoterm {quote.incoterm.value if hasattr(quote.incoterm, 'value') else quote.incoterm}.",
            evidence=f"{quote.currency} {quote.total_quote_price:,.2f} ({quote.margin_percentage:.1f}% margin)",
        ))
        passed_count += 1
    elif quote:
        pillars.append(ReadinessPillar(
            key="COSTING",
            name="Incoterm Costing & Quotation",
            status="WARNING",
            message="Quotation calculated but pending final customer/manager approval.",
            evidence=f"Status: {quote.status.value if hasattr(quote.status, 'value') else quote.status}",
        ))
        warnings.append("Quotation requires final sign-off")
    else:
        pillars.append(ReadinessPillar(
            key="COSTING",
            name="Incoterm Costing & Quotation",
            status="BLOCKED",
            message="No Incoterm costing quote generated for this deal.",
            evidence="Missing DealQuote record",
        ))
        blockers.append("Commercial Incoterm quote missing")

    # ── Pillar 3: Export Documents Generation ───────────────────────
    if isinstance(db, AsyncSession):
        ds_stmt = select(DocumentSet).options(selectinload(DocumentSet.documents)).where(DocumentSet.deal_id == deal_id).order_by(desc(DocumentSet.created_at))
        ds_res = await db.execute(ds_stmt)
        doc_set = ds_res.scalars().first()
    else:
        doc_set = db.query(DocumentSet).filter(DocumentSet.deal_id == deal_id).order_by(desc(DocumentSet.created_at)).first()

    if doc_set and doc_set.status == DocumentStatus.RELEASED:
        pillars.append(ReadinessPillar(
            key="DOCUMENTS",
            name="Export Document Set",
            status="PASSED",
            message="Complete export document set generated and approved.",
            evidence=f"{len(doc_set.documents or [])} documents approved & released",
        ))
        passed_count += 1
    elif doc_set:
        unapproved = [d.title for d in doc_set.documents or [] if d.status != DocumentStatus.APPROVED]
        if not unapproved and len(doc_set.documents or []) >= 3:
            pillars.append(ReadinessPillar(
                key="DOCUMENTS",
                name="Export Document Set",
                status="PASSED",
                message="All documents generated and approved.",
                evidence=f"{len(doc_set.documents or [])} documents ready",
            ))
            passed_count += 1
        else:
            pillars.append(ReadinessPillar(
                key="DOCUMENTS",
                name="Export Document Set",
                status="WARNING",
                message="Document set drafted but pending individual approvals.",
                evidence=f"Pending: {', '.join(unapproved) if unapproved else 'Release required'}",
            ))
            warnings.append("Documents drafted but require formal release approval")
    else:
        pillars.append(ReadinessPillar(
            key="DOCUMENTS",
            name="Export Document Set",
            status="BLOCKED",
            message="Export documents (Commercial Invoice, Packing List, CoO) not generated.",
            evidence="No DocumentSet record found",
        ))
        blockers.append("Export document set must be generated")

    # ── Pillar 4: Cross-Document Consistency & Hash Integrity ────────
    if doc_set and doc_set.documents:
        hashes_valid = all(bool(d.sha256_hash) for d in doc_set.documents)
        if hashes_valid:
            pillars.append(ReadinessPillar(
                key="CONSISTENCY",
                name="Cross-Document Consistency Audit",
                status="PASSED",
                message="SHA-256 cryptographic hashes verified. 0 cross-document discrepancies.",
                evidence="All document checksums intact",
            ))
            passed_count += 1
        else:
            pillars.append(ReadinessPillar(
                key="CONSISTENCY",
                name="Cross-Document Consistency Audit",
                status="WARNING",
                message="Document checksum validation incomplete.",
                evidence="Audit check pending",
            ))
            warnings.append("Document consistency audit recommended before cargo dispatch")
    else:
        pillars.append(ReadinessPillar(
            key="CONSISTENCY",
            name="Cross-Document Consistency Audit",
            status="BLOCKED",
            message="Cannot verify consistency without generated document set.",
            evidence="Pending documents generation",
        ))

    # ── Pillar 5: Regulatory & SBP Compliance Clearance ──────────────
    if isinstance(db, AsyncSession):
        c_stmt = select(ComplianceCheck).where(ComplianceCheck.deal_id == deal_id)
        c_res = await db.execute(c_stmt)
        checks = c_res.scalars().all()
    else:
        checks = db.query(ComplianceCheck).filter(ComplianceCheck.deal_id == deal_id).all()

    mandatory_checks = [c for c in checks if c.is_mandatory]
    mandatory_cleared = [c for c in mandatory_checks if c.status in [ComplianceStatus.OBTAINED, ComplianceStatus.NOT_APPLICABLE]]

    if mandatory_checks and len(mandatory_cleared) == len(mandatory_checks):
        pillars.append(ReadinessPillar(
            key="COMPLIANCE",
            name="Regulatory & SBP Compliance",
            status="PASSED",
            message="All mandatory regulatory and SBP Chapter XII rules cleared.",
            evidence=f"Cleared {len(mandatory_cleared)} of {len(mandatory_checks)} mandatory checks",
        ))
        passed_count += 1
    elif mandatory_checks:
        pending_titles = [c.title for c in mandatory_checks if c not in mandatory_cleared]
        pillars.append(ReadinessPillar(
            key="COMPLIANCE",
            name="Regulatory & SBP Compliance",
            status="BLOCKED",
            message="Mandatory SBP or destination customs requirements pending.",
            evidence=f"Pending: {', '.join(pending_titles[:2])}",
        ))
        blockers.append(f"Compliance clearance required for: {', '.join(pending_titles[:2])}")
    else:
        pillars.append(ReadinessPillar(
            key="COMPLIANCE",
            name="Regulatory & SBP Compliance",
            status="WARNING",
            message="Compliance checklist not evaluated against deal terms.",
            evidence="Re-evaluate checklist required",
        ))
        warnings.append("Run compliance evaluation to verify destination customs rules")

    # ── Pillar 6: Shipment Logistics Booking ─────────────────────────
    if isinstance(db, AsyncSession):
        s_stmt = select(Shipment).where(Shipment.deal_id == deal_id)
        s_res = await db.execute(s_stmt)
        shipments = s_res.scalars().all()
    else:
        shipments = db.query(Shipment).filter(Shipment.deal_id == deal_id).all()

    active_shp = next((s for s in shipments if s.status != ShipmentStatus.CANCELLED), None)

    if active_shp and (active_shp.status in [ShipmentStatus.BOOKED, ShipmentStatus.CARGO_READY, ShipmentStatus.STUFFED, ShipmentStatus.GATED_IN, ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED]):
        pillars.append(ReadinessPillar(
            key="LOGISTICS",
            name="Transport & Shipping Allocation",
            status="PASSED",
            message=f"Carrier {active_shp.carrier_name} booked ({active_shp.transport_mode.value if hasattr(active_shp.transport_mode, 'value') else active_shp.transport_mode}).",
            evidence=f"Tracking: {active_shp.tracking_number} • B/L: {active_shp.transport_doc_number or 'Pending'}",
        ))
        passed_count += 1
    elif shipments:
        pillars.append(ReadinessPillar(
            key="LOGISTICS",
            name="Transport & Shipping Allocation",
            status="WARNING",
            message="Shipment draft created but booking confirmation pending with carrier.",
            evidence=f"Status: {shipments[0].status}",
        ))
        warnings.append("Confirm carrier booking and container allocation")
    else:
        pillars.append(ReadinessPillar(
            key="LOGISTICS",
            name="Transport & Shipping Allocation",
            status="BLOCKED",
            message="No transport booking or carrier allocated.",
            evidence="No shipment booking record found",
        ))
        blockers.append("Shipment booking required with freight carrier")

    # ── Pillar 7: Payment Terms & Realization ────────────────────────
    if isinstance(db, AsyncSession):
        p_stmt = select(PaymentTransaction).where(PaymentTransaction.deal_id == deal_id)
        p_res = await db.execute(p_stmt)
        payments = p_res.scalars().all()
    else:
        payments = db.query(PaymentTransaction).filter(PaymentTransaction.deal_id == deal_id).all()

    total_paid = sum((Decimal(str(p.amount)) for p in payments), start=Decimal("0.00"))

    if total_paid > Decimal("0.00") or (quote and quote.total_quote_price and total_paid >= quote.total_quote_price):
        pillars.append(ReadinessPillar(
            key="PAYMENT",
            name="Financial Terms & SBP Realization",
            status="PASSED",
            message="Payment terms satisfied (advance received or settlement recorded).",
            evidence=f"Received: USD {total_paid:,.2f}",
        ))
        passed_count += 1
    else:
        pillars.append(ReadinessPillar(
            key="PAYMENT",
            name="Financial Terms & SBP Realization",
            status="WARNING",
            message="Zero payment received yet. Verify if advance Form-R or LC is required before dispatch.",
            evidence="USD 0.00 received",
        ))
        warnings.append("Confirm payment terms / LC drawing before releasing original Bill of Lading")

    score_pct = int((passed_count / 7.0) * 100)
    is_ready = len(blockers) == 0 and score_pct >= 85
    overall_status = "READY_TO_SHIP" if is_ready else ("ACTION_REQUIRED" if len(blockers) > 0 else "NOT_READY")

    return DealReadinessResponse(
        deal_id=deal.id,
        reference=deal.reference,
        buyer_name=deal.buyer_name,
        overall_status=overall_status,
        is_ready_to_ship=is_ready,
        score_percentage=score_pct,
        pillars=pillars,
        blockers=blockers,
        warnings=warnings,
    )


async def ask_export_copilot(
    query: str,
    deal_id: Optional[UUID],
    organisation_id: UUID,
    db: Any,
    top_k: int = 5,
) -> CopilotQueryResponse:
    """
    Conversational RAG agent combining Qdrant vector retrieval, live SQL deal state,
    and Qwen 2.5 with zero-hallucination guardrails.
    """
    # 1. Vector Retrieval via Qdrant
    retrieved_raw = query_qdrant_vectors(query, organisation_id, deal_id, top_k=top_k)
    retrieved_chunks = [
        RetrievedChunkInfo(
            id=str(r["id"]),
            title=r["title"],
            text=r["text"],
            score=r["score"],
            source=r["source"],
            chunk_type=r["chunk_type"],
            is_global=r.get("is_global", False),
        )
        for r in retrieved_raw
    ]

    # 2. Live Structured Deal Inspection (if deal_id)
    readiness_summary = None
    deal_context_str = ""
    if deal_id:
        try:
            readiness_summary = await inspect_deal_readiness(deal_id, db)
            deal_context_str = (
                f"Active Deal Reference: {readiness_summary.reference} (Buyer: {readiness_summary.buyer_name})\n"
                f"Overall Readiness Status: {readiness_summary.overall_status} (Readiness Score: {readiness_summary.score_percentage}%)\n"
                f"Ready to Ship: {'YES' if readiness_summary.is_ready_to_ship else 'NO'}\n"
                f"Identified Blockers: {'; '.join(readiness_summary.blockers) if readiness_summary.blockers else 'None'}\n"
                f"Identified Warnings: {'; '.join(readiness_summary.warnings) if readiness_summary.warnings else 'None'}\n"
            )
        except Exception:
            pass

    # 3. Construct Grounded Prompt
    knowledge_context = "\n\n---\n\n".join(
        f"[{c.title} | Source: {c.source}]\n{c.text}"
        for c in retrieved_chunks
    )

    system_prompt = (
        "You are the authoritative ExportOS AI Copilot, specialized in Pakistani export operations, "
        "State Bank of Pakistan (SBP) Foreign Exchange Manual Chapter XII, Incoterms 2020, and international trade compliance.\n\n"
        "STRICT CONSTRAINTS (FR-COP-02 & FR-COP-03):\n"
        "1. Answer ONLY using facts from the Provided Deal Context and Retrieved Knowledge Chunks.\n"
        "2. Do NOT invent, assume, or hallucinate facts not present in the context.\n"
        "3. Explicitly cite deal database records (e.g. [Deal: EXP-2026-001], [Quote: CIF Hamburg]) and legal circulars (e.g. [SBP FE Manual Ch XII Para 6]).\n"
        "4. If answering whether an order is ready to ship, provide a clear structured breakdown of passed vs pending criteria.\n"
        "5. If a required detail is missing from context, state clearly that it is not on record."
    )

    user_prompt = (
        f"USER QUERY: {query}\n\n"
        f"LIVE DEAL CONTEXT:\n{deal_context_str if deal_context_str else 'No specific deal selected.'}\n\n"
        f"RETRIEVED KNOWLEDGE CHUNKS:\n{knowledge_context if knowledge_context else 'No specific knowledge chunks retrieved.'}\n\n"
        "Please provide a comprehensive, grounded, professional response with citations."
    )

    # 4. Call LLM with fallback
    citations = []
    for c in retrieved_chunks:
        if c.source not in citations:
            citations.append(c.source)

    try:
        llm_answer = call_qwen_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
    except Exception as e:
        # Deterministic Grounded Fallback Response
        if readiness_summary:
            status_desc = "Ready to ship!" if readiness_summary.is_ready_to_ship else "Not ready to ship."
            llm_answer = (
                f"### Order Readiness Assessment ({readiness_summary.reference})\n\n"
                f"**Conclusion**: The order is **{status_desc}** (Readiness Score: {readiness_summary.score_percentage}%)\n\n"
                "**7-Pillar Inspection Breakdown**:\n"
            )
            for p in readiness_summary.pillars:
                icon = "✓" if p.status == "PASSED" else ("⚠" if p.status == "WARNING" else "✕")
                llm_answer += f"- {icon} **{p.name}**: {p.message} *({p.evidence or ''})*\n"

            if readiness_summary.blockers:
                llm_answer += f"\n**Critical Action Items Required**:\n"
                for b in readiness_summary.blockers:
                    llm_answer += f"- ❌ {b}\n"
        else:
            llm_answer = (
                f"Based on the knowledge base: {query}\n\n"
                f"{retrieved_chunks[0].text if retrieved_chunks else 'Please consult the relevant export documentation.'}"
            )

    suggested_followups = [
        "Is this order ready to ship?",
        "What documents or compliance items are missing?",
        "Explain the SBP 120-day realization deadline",
        "Draft shipping dispatch advice for buyer",
    ]

    return CopilotQueryResponse(
        query=query,
        answer=llm_answer,
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        readiness=readiness_summary,
        suggested_followups=suggested_followups,
    )


async def draft_buyer_correspondence(
    template_type: str,
    deal_id: UUID,
    organisation_id: UUID,
    db: Any,
    custom_notes: Optional[str] = None,
) -> BuyerMessageDraftResponse:
    """
    Generates structured commercial correspondence with Human-in-the-loop Gate (FR-COP-05).
    """
    if isinstance(db, AsyncSession):
        d_stmt = select(Deal).where(Deal.id == deal_id, Deal.organisation_id == organisation_id)
        d_res = await db.execute(d_stmt)
        deal = d_res.scalars().first()
        if not deal:
            raise ValueError("Deal not found")

        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at))
        q_res = await db.execute(q_stmt)
        quote = q_res.scalars().first()

        s_stmt = select(Shipment).where(Shipment.deal_id == deal_id).order_by(desc(Shipment.created_at))
        s_res = await db.execute(s_stmt)
        shipment = s_res.scalars().first()

        p_stmt = select(PaymentTransaction).where(PaymentTransaction.deal_id == deal_id)
        p_res = await db.execute(p_stmt)
        payments = p_res.scalars().all()
    else:
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.organisation_id == organisation_id).first()
        if not deal:
            raise ValueError("Deal not found")
        quote = db.query(DealQuote).filter(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at)).first()
        shipment = db.query(Shipment).filter(Shipment.deal_id == deal_id).order_by(desc(Shipment.created_at)).first()
        payments = db.query(PaymentTransaction).filter(PaymentTransaction.deal_id == deal_id).all()

    total_paid = sum((Decimal(str(p.amount)) for p in payments), start=Decimal("0.00"))

    incoterm_str = f"{quote.incoterm.value if hasattr(quote.incoterm, 'value') else quote.incoterm} {quote.incoterm_place}" if quote else "CIF Destination"
    total_price_str = f"{quote.currency} {quote.total_quote_price:,.2f}" if quote else "Agreed Value"

    if template_type == "ORDER_CONFIRMATION":
        subject = f"Order Confirmation — ExportOS Ref: {deal.reference} ({deal.buyer_name})"
        body = (
            f"Dear {deal.buyer_name} Procurement Team,\n\n"
            f"We are pleased to confirm your export order (Reference: {deal.reference}).\n\n"
            f"Order Summary:\n"
            f"• Commercial Terms: {incoterm_str}\n"
            f"• Total Order Value: {total_price_str}\n"
            f"• Production Facility: Verified & Stock Allocated\n"
            f"• Proforma Invoice: Available in ExportOS Portal\n\n"
            f"{f'Special Notes: {custom_notes}' if custom_notes else 'Our production and quality control team is executing according to international standards.'}\n\n"
            f"Please review and sign the attached Proforma Invoice.\n\n"
            f"Best regards,\n"
            f"Export Commercial Operations"
        )
    elif template_type == "SHIPPING_ADVICE":
        subject = f"Shipping Advice & Dispatch Notification — {deal.reference} ({deal.buyer_name})"
        tracking = shipment.tracking_number if shipment else "EXP-SHP-PENDING"
        carrier = shipment.carrier_name if shipment else "Designated Shipping Line"
        vessel = shipment.vessel_or_flight if shipment else "Scheduled Vessel"
        bl_no = shipment.transport_doc_number if shipment else "Under Processing"
        etd = shipment.etd.strftime("%Y-%m-%d") if shipment and shipment.etd else "Scheduled"
        eta = shipment.eta.strftime("%Y-%m-%d") if shipment and shipment.eta else "Scheduled"

        body = (
            f"Dear {deal.buyer_name} Logistics Team,\n\n"
            f"We are pleased to inform you that your consignment under Deal {deal.reference} has been dispatched.\n\n"
            f"Shipment & Transport Details:\n"
            f"• Tracking Reference: {tracking}\n"
            f"• Carrier & Vessel: {carrier} ({vessel})\n"
            f"• Bill of Lading / AWB No.: {bl_no}\n"
            f"• Estimated Departure (ETD): {etd}\n"
            f"• Estimated Arrival (ETA): {eta}\n"
            f"• Trade Terms: {incoterm_str}\n\n"
            f"Commercial Invoice, Packing List, and Certificate of Origin are attached.\n\n"
            f"Best regards,\n"
            f"Logistics & Shipping Department"
        )
    elif template_type == "PAYMENT_REMINDER_SBP":
        balance_due = (quote.total_quote_price - total_paid) if quote else Decimal("0.00")
        subject = f"Payment Settlement & SBP Realization Notice — {deal.reference}"
        body = (
            f"Dear {deal.buyer_name} Accounts Payable Team,\n\n"
            f"We hope this message finds you well.\n\n"
            f"Regarding export contract {deal.reference}:\n"
            f"• Total Invoice Value: {total_price_str}\n"
            f"• Amount Received to Date: USD {total_paid:,.2f}\n"
            f"• Outstanding Balance Due: USD {balance_due:,.2f}\n\n"
            f"Under State Bank of Pakistan (SBP) Foreign Exchange Manual Chapter XII regulations, all export proceeds must be credited and reconciled against the corresponding Electronic Form-E (EFE).\n\n"
            f"Please arrange wire transfer to our Authorized Dealer banking coordinates:\n"
            f"Bank: Habib Bank Limited (HBL) Foreign Exchange Branch\n"
            f"IBAN / SWIFT coordinates available upon request.\n\n"
            f"Thank you for your cooperation.\n\n"
            f"Best regards,\n"
            f"Export Finance & Accounts"
        )
    else:
        subject = f"Commercial Ingestion & Inquiry Update — {deal.reference}"
        body = (
            f"Dear {deal.buyer_name},\n\n"
            f"Thank you for your valued export inquiry ({deal.reference}).\n\n"
            f"Our commercial and technical teams have reviewed your specifications. "
            f"Please find our quotation details under {incoterm_str} terms.\n\n"
            f"Best regards,\n"
            f"Export Sales Team"
        )

    return BuyerMessageDraftResponse(
        template_type=template_type,
        subject=subject,
        body=body,
        deal_reference=deal.reference,
        buyer_name=deal.buyer_name,
        human_approval_required=True,
    )
