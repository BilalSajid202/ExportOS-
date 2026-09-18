"""
ExportOS — Compliance Rule Engine

Deterministic rules engine assembling required document checklists and
regulatory obligations based on destination country, Incoterms 2020,
product categories, and State Bank of Pakistan Foreign Exchange regulations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance import (
    ComplianceCategory,
    ComplianceCheck,
    ComplianceStatus,
)
from app.models.costing import DealQuote, Incoterm, QuoteStatus
from app.models.deal import Deal, DealLineItem
from app.models.user import User


def get_rule_definitions_for_deal(deal: Deal, active_quote: Optional[DealQuote] = None) -> list[dict]:
    """
    Pure deterministic function generating rule definitions matching deal parameters.
    """
    destination_parts = []
    if active_quote and active_quote.incoterm_place:
        destination_parts.append(active_quote.incoterm_place)
    if deal.notes:
        destination_parts.append(deal.notes)
    if deal.buyer_name:
        destination_parts.append(deal.buyer_name)
    destination = " ".join(destination_parts).strip().upper()

    incoterm_str = (
        (active_quote.incoterm.value if active_quote and active_quote.incoterm else "FOB")
    ).upper()

    payment_method = (deal.notes or "").strip().upper()

    # Collect product descriptions / names for category matching
    product_texts = []
    if deal.line_items:
        for li in deal.line_items:
            p_name = li.product.name if li.product else ""
            p_sku = li.product.sku if li.product else ""
            p_desc = li.description or ""
            product_texts.append(f"{p_name} {p_sku} {p_desc}".lower())
    combined_products = " ".join(product_texts)

    rules = []

    # ─────────────────────────────────────────────────────────────
    # 1. State Bank of Pakistan (SBP) & Pakistan Single Window
    # ─────────────────────────────────────────────────────────────
    rules.append({
        "rule_code": "SBP_E_FORM_E",
        "category": ComplianceCategory.REGULATORY_SBP,
        "title": "SBP Electronic Form-E (EFE) via Pakistan Single Window (PSW)",
        "description": (
            "Mandatory under SBP Foreign Exchange Manual Chapter XII. The exporter must "
            "submit and obtain approved Electronic Form-E (EFE) via the Pakistan Single Window "
            "portal before customs goods declaration (GD) filing and cargo gate-in."
        ),
        "authority": "State Bank of Pakistan (SBP) / Pakistan Single Window (PSW)",
        "is_mandatory": True,
        "responsible_role": "DOCUMENTATION_OFFICER",
    })

    rules.append({
        "rule_code": "SBP_PROCEEDS_120D",
        "category": ComplianceCategory.REGULATORY_SBP,
        "title": "SBP 120-Day Export Proceeds Realization Commitment",
        "description": (
            "Per SBP FE Circular No. 03, foreign exchange proceeds from exports must be "
            "realized and repatriated through the Authorized Dealer (AD) bank within 120 days "
            "from the date of shipment/bill of lading."
        ),
        "authority": "State Bank of Pakistan (SBP)",
        "is_mandatory": True,
        "responsible_role": "ACCOUNTS",
    })

    if "ADVANCE" in payment_method or "TT" in payment_method:
        rules.append({
            "rule_code": "SBP_ADVANCE_REALIZATION",
            "category": ComplianceCategory.PAYMENT_TERMS,
            "title": "SBP Advance Payment Realization Certificate (Form-R)",
            "description": (
                "Advance remittance received must be documented with an official Bank "
                "Realization Certificate (BRC / Form-R) issued by the Authorized Dealer bank."
            ),
            "authority": "Authorized Dealer Bank / SBP",
            "is_mandatory": True,
            "responsible_role": "ACCOUNTS",
        })

    if "LC" in payment_method or "LETTER OF CREDIT" in payment_method or "DOCUMENTARY CREDIT" in payment_method:
        rules.append({
            "rule_code": "UCP600_LC_COMPLIANCE",
            "category": ComplianceCategory.PAYMENT_TERMS,
            "title": "ICC UCP 600 Letter of Credit Documentary Scrutiny",
            "description": (
                "All shipping documents must conform strictly to the terms of the Letter of Credit "
                "under ICC Uniform Customs and Practice for Documentary Credits (UCP 600) to avoid bank discrepancies."
            ),
            "authority": "International Chamber of Commerce (ICC) / Issuing Bank",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    # ─────────────────────────────────────────────────────────────
    # 2. Incoterm 2020 Specific Obligations
    # ─────────────────────────────────────────────────────────────
    if incoterm_str in ["CIF", "CIP"]:
        rules.append({
            "rule_code": "INCOTERM_CIF_INSURANCE",
            "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
            "title": "Marine Cargo Insurance Policy (Institute Cargo Clauses A/C)",
            "description": (
                f"Under {incoterm_str}, the seller is contractually obligated to obtain marine cargo insurance "
                "covering minimum 110% of the invoice value in the contract currency, issued by a rated underwriter."
            ),
            "authority": "ICC Incoterms 2020 / Marine Underwriters",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if incoterm_str == "FOB":
        rules.append({
            "rule_code": "INCOTERM_FOB_FORWARDER_NOTICE",
            "category": ComplianceCategory.SHIPPING_CUSTOMS,
            "title": "Buyer Nominated Forwarder Routing Order & Booking Ref",
            "description": (
                "Under FOB terms, the overseas buyer must furnish carrier nomination details and origin "
                "booking reference at Karachi/Qasim Port prior to factory container loading."
            ),
            "authority": "ICC Incoterms 2020 / Shipping Line",
            "is_mandatory": False,
            "responsible_role": "EXPORT_MANAGER",
        })

    if incoterm_str == "DDP":
        rules.append({
            "rule_code": "INCOTERM_DDP_IMPORT_CLEARANCE",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "Destination Import Customs Clearance & VAT/Duty Settlement",
            "description": (
                "Under DDP, the Pakistani exporter bears all risks and costs to destination door, "
                "including payment of destination import customs tariffs, VAT, and terminal clearance."
            ),
            "authority": "Destination Customs Authority",
            "is_mandatory": True,
            "responsible_role": "EXPORT_MANAGER",
        })

    # ─────────────────────────────────────────────────────────────
    # 3. Destination Country Specific Rules
    # ─────────────────────────────────────────────────────────────
    eu_countries = [
        "GERMANY", "DE", "FRANCE", "FR", "ITALY", "IT", "NETHERLANDS", "NL",
        "SPAIN", "ES", "BELGIUM", "BE", "POLAND", "PL", "SWEDEN", "SE",
        "DENMARK", "DK", "PORTUGAL", "PT", "AUSTRIA", "AT", "EU", "EUROPE",
    ]
    is_eu = any(c in destination for c in eu_countries)

    if is_eu:
        rules.append({
            "rule_code": "EU_REX_GSP_PLUS",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "EU Registered Exporter (REX) Statement on Origin (GSP+)",
            "description": (
                "Under the EU GSP+ preferential tariff scheme, the Pakistani exporter must include their "
                "official REX number and Statement on Origin on the Commercial Invoice for zero-duty clearance in the EU."
            ),
            "authority": "European Commission / TDAP Pakistan",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if any(us in destination for us in ["USA", "US", "UNITED STATES", "AMERICA"]):
        rules.append({
            "rule_code": "US_CBP_ISF_FILING",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "US CBP Importer Security Filing (10+2) Compliance",
            "description": (
                "For ocean shipments to the US, manufacturer, container stuffing, and consolidator data "
                "must be transmitted to US Customs and Border Protection at least 24 hours before vessel departure."
            ),
            "authority": "US Customs and Border Protection (CBP)",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if any(uk in destination for uk in ["UK", "UNITED KINGDOM", "ENGLAND", "BRITAIN", "GB"]):
        rules.append({
            "rule_code": "UK_DCTS_ORIGIN_DECLARATION",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "UK Developing Countries Trading Scheme (DCTS) Origin Declaration",
            "description": (
                "Preferential tariff clearance in the UK requires a compliant DCTS origin declaration "
                "stipulating qualifying local value addition in Pakistan."
            ),
            "authority": "HM Revenue & Customs (HMRC)",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if any(gcc in destination for gcc in ["UAE", "DUBAI", "SAUDI", "KSA", "QATAR", "OMAN", "KUWAIT", "BAHRAIN"]):
        rules.append({
            "rule_code": "GCC_CHAMBER_ATTESTATION",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "Chamber of Commerce Certificate of Origin Attestation",
            "description": (
                "Commercial invoices and certificates of origin for Arabian Gulf destinations "
                "require formal attestation by the local Chamber of Commerce (e.g. SCCI / LCCI / KCCI)."
            ),
            "authority": "Chamber of Commerce & Industry / Destination Customs",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if not is_eu and not any(us in destination for us in ["USA", "US", "UNITED STATES"]):
        rules.append({
            "rule_code": "STANDARD_CERTIFICATE_OF_ORIGIN",
            "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
            "title": "Certificate of Origin (TDAP / Chamber of Commerce)",
            "description": (
                "Authoritative Certificate of Origin proving goods were manufactured in Pakistan, "
                "issued by the Trade Development Authority of Pakistan or registered Chamber of Commerce."
            ),
            "authority": "Trade Development Authority of Pakistan (TDAP)",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    # ─────────────────────────────────────────────────────────────
    # 4. Product Category Specific Requirements
    # ─────────────────────────────────────────────────────────────
    if any(k in combined_products for k in ["football", "soccer", "ball", "sport", "leather", "glove", "boxing"]):
        rules.append({
            "rule_code": "REACH_CHEMICAL_CONFORMITY",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "EU REACH & Heavy Metal Safety Declaration (Azo Dyes & Chromium VI)",
            "description": (
                "Sports goods and leather articles must comply with EU REACH Annex XVII restrictions "
                "confirming total absence of prohibited azo colorants, phthalates, and hexavalent chromium."
            ),
            "authority": "European Chemicals Agency (ECHA)",
            "is_mandatory": True if is_eu else False,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if any(k in combined_products for k in ["textile", "fabric", "cotton", "garment", "t-shirt", "denim", "towel", "sheet"]):
        rules.append({
            "rule_code": "TEXTILE_FIBER_COMPOSITION",
            "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
            "title": "Textile Fiber Composition & Care Labeling Declaration",
            "description": (
                "Mandatory declaration specifying 100% cotton / blend ratios and international care code symbols "
                "in conformity with ISO 3758 standards."
            ),
            "authority": "Pakistan Standards & Quality Control Authority (PSQCA)",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    if any(k in combined_products for k in ["surgical", "instrument", "forceps", "scissors", "medical"]):
        rules.append({
            "rule_code": "SURGICAL_ISO13485_MDR",
            "category": ComplianceCategory.DESTINATION_CUSTOMS,
            "title": "Medical Device Regulation (MDR) & ISO 13485 Compliance",
            "description": (
                "Surgical instruments require technical file documentation, ISO 13485 certificate, "
                "and CE marking conformity declaration for clinical safety."
            ),
            "authority": "EU MDR / DRAP (Drug Regulatory Authority of Pakistan)",
            "is_mandatory": True,
            "responsible_role": "EXPORT_MANAGER",
        })

    if any(k in combined_products for k in ["rice", "mango", "fruit", "spice", "food", "agri", "wheat"]):
        rules.append({
            "rule_code": "DPP_PHYTOSANITARY_CERT",
            "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
            "title": "Department of Plant Protection (DPP) Phytosanitary & Fumigation Certificate",
            "description": (
                "Agricultural goods must undergo quarantine inspection and fumigation treatment, "
                "with an official Phytosanitary Certificate issued by DPP Pakistan."
            ),
            "authority": "Department of Plant Protection (DPP), Govt of Pakistan",
            "is_mandatory": True,
            "responsible_role": "DOCUMENTATION_OFFICER",
        })

    # ─────────────────────────────────────────────────────────────
    # 5. Mandatory Documentary Execution
    # ─────────────────────────────────────────────────────────────
    rules.append({
        "rule_code": "COMMERCIAL_INVOICE_FINAL",
        "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
        "title": "Signed & Stamped Commercial Invoice with WeBOC NTN/STRN",
        "description": (
            "Final Commercial Invoice bearing company seal, signature, bank IBAN, "
            "National Tax Number (NTN), and Sales Tax Registration Number (STRN)."
        ),
        "authority": "Pakistan Customs (WeBOC)",
        "is_mandatory": True,
        "responsible_role": "EXPORT_MANAGER",
    })

    rules.append({
        "rule_code": "PACKING_LIST_VERIFICATION",
        "category": ComplianceCategory.DOCUMENTARY_MANDATORY,
        "title": "Export Packing List with Verified Gross Mass (VGM)",
        "description": (
            "Detailed breakdown of cartons, individual piece counts, net weights, and "
            "SOLAS Verified Gross Mass (VGM) for ocean container loading."
        ),
        "authority": "Pakistan Customs / IMO SOLAS",
        "is_mandatory": True,
        "responsible_role": "DOCUMENTATION_OFFICER",
    })

    return rules


async def ensure_deal_compliance_checks(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    deal_id: uuid.UUID,
    *,
    force_regenerate: bool = False,
) -> List[ComplianceCheck]:
    """
    Fetches compliance checks for deal; generates deterministic checklist if missing or forced.
    """
    # 1. Fetch deal with line items and quotes
    result = await db.execute(
        select(Deal)
        .options(
            selectinload(Deal.line_items).selectinload(DealLineItem.product),
            selectinload(Deal.quotes),
        )
        .where(
            Deal.id == deal_id,
            Deal.organisation_id == organisation_id,
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise ValueError("Deal not found in this organisation")

    # Determine active approved quote if any
    active_quote = next(
        (q for q in deal.quotes if q.status == QuoteStatus.APPROVED),
        deal.quotes[0] if deal.quotes else None,
    )

    # 2. Check existing checks
    existing_result = await db.execute(
        select(ComplianceCheck)
        .where(
            ComplianceCheck.deal_id == deal_id,
            ComplianceCheck.organisation_id == organisation_id,
        )
        .order_by(ComplianceCheck.created_at.asc())
    )
    existing_checks = list(existing_result.scalars().all())

    if existing_checks and not force_regenerate:
        return existing_checks

    rule_defs = get_rule_definitions_for_deal(deal, active_quote)

    if force_regenerate and existing_checks:
        # Preserve status/notes of existing matching rule_codes
        status_map = {
            c.rule_code: (c.status, c.notes, c.evidence_ref, c.completed_by, c.completed_at)
            for c in existing_checks
        }
        await db.execute(
            delete(ComplianceCheck).where(
                ComplianceCheck.deal_id == deal_id,
                ComplianceCheck.organisation_id == organisation_id,
            )
        )
        await db.flush()
    else:
        status_map = {}

    created_checks = []
    for r in rule_defs:
        prev = status_map.get(r["rule_code"])
        c_status = prev[0] if prev else ComplianceStatus.NOT_STARTED
        c_notes = prev[1] if prev else None
        c_evidence = prev[2] if prev else None
        c_by = prev[3] if prev else None
        c_at = prev[4] if prev else None

        check = ComplianceCheck(
            organisation_id=organisation_id,
            deal_id=deal_id,
            rule_code=r["rule_code"],
            category=r["category"],
            title=r["title"],
            description=r["description"],
            authority=r["authority"],
            status=c_status,
            is_mandatory=r["is_mandatory"],
            responsible_role=r["responsible_role"],
            notes=c_notes,
            evidence_ref=c_evidence,
            completed_by=c_by,
            completed_at=c_at,
        )
        db.add(check)
        created_checks.append(check)

    await db.flush()
    return created_checks


async def update_compliance_check(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    check_id: uuid.UUID,
    status: ComplianceStatus,
    notes: Optional[str],
    evidence_ref: Optional[str],
    user: User,
) -> ComplianceCheck:
    """Updates status and evidence of a compliance check item."""
    result = await db.execute(
        select(ComplianceCheck).where(
            ComplianceCheck.id == check_id,
            ComplianceCheck.organisation_id == organisation_id,
        )
    )
    check = result.scalar_one_or_none()
    if not check:
        raise ValueError("Compliance check not found")

    check.status = status
    if notes is not None:
        check.notes = notes
    if evidence_ref is not None:
        check.evidence_ref = evidence_ref

    if status in [ComplianceStatus.OBTAINED, ComplianceStatus.WAIVED, ComplianceStatus.NOT_APPLICABLE]:
        check.completed_by = user.id
        check.completed_at = datetime.now(timezone.utc)
    else:
        check.completed_by = None
        check.completed_at = None

    await db.flush()
    return check


async def compute_compliance_summary(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    deal_id: uuid.UUID,
) -> dict:
    """Computes overall compliance completion and mandatory status."""
    checks = await ensure_deal_compliance_checks(db, organisation_id, deal_id)

    total_checks = len(checks)
    mandatory_checks = [c for c in checks if c.is_mandatory]
    mandatory_total = len(mandatory_checks)

    cleared_statuses = [
        ComplianceStatus.OBTAINED,
        ComplianceStatus.WAIVED,
        ComplianceStatus.NOT_APPLICABLE,
    ]

    mandatory_completed = sum(1 for c in mandatory_checks if c.status in cleared_statuses)
    mandatory_pending = mandatory_total - mandatory_completed

    all_completed = sum(1 for c in checks if c.status in cleared_statuses)
    completion_percentage = (
        Decimal(round((all_completed / total_checks) * 100, 1))
        if total_checks > 0
        else Decimal("100.0")
    )

    is_fully_compliant = mandatory_pending == 0

    return {
        "deal_id": deal_id,
        "total_checks": total_checks,
        "mandatory_total": mandatory_total,
        "mandatory_completed": mandatory_completed,
        "mandatory_pending": mandatory_pending,
        "is_fully_compliant": is_fully_compliant,
        "completion_percentage": completion_percentage,
        "checks": checks,
    }
