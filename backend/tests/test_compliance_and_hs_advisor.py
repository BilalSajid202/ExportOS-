"""
Unit tests for Phase 12: Compliance Engine, SBP Regulations & HS Advisor.
"""

from decimal import Decimal
import uuid
import pytest

from app.models.compliance import (
    ComplianceCategory,
    ComplianceStatus,
    HSClassificationStatus,
)
from app.models.costing import DealQuote, Incoterm, QuoteStatus
from app.models.deal import Deal, DealLineItem, DealState
from app.models.product import Product
from app.services.compliance import get_rule_definitions_for_deal
from app.services.hs_advisor import match_pct_taxonomy
from app.services.sbp_regulations import query_sbp_regulations


def test_compliance_rules_for_eu_cif_sports_deal():
    """
    Test scenario:
    Sialkot exporter sending Footballs to Germany under CIF Hamburg terms.
    Expected rules:
      1. SBP Electronic Form-E (Mandatory)
      2. SBP 120-Day Proceeds Realization (Mandatory)
      3. Marine Cargo Insurance Policy (Mandatory under CIF)
      4. EU REX Statement on Origin GSP+ (Mandatory for Germany)
      5. EU REACH Chemical Safety Declaration (Mandatory for Sports/Leather to EU)
      6. Commercial Invoice & Packing List (Mandatory)
    """
    deal = Deal(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        reference="DEAL-2026-001",
        buyer_name="German Sports GmbH",
        state=DealState.INQUIRY,
        notes="Destination: Hamburg, Germany. Payment: Documentary Letter of Credit",
    )
    product = Product(
        id=uuid.uuid4(),
        organisation_id=deal.organisation_id,
        sku="FB-S5-001",
        name="Size-5 Match Football",
        unit_of_measure="PCS",
    )
    line_item = DealLineItem(
        id=uuid.uuid4(),
        deal_id=deal.id,
        product_id=product.id,
        quantity=Decimal("5000"),
        product=product,
    )
    deal.line_items = [line_item]

    active_quote = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal.id,
        organisation_id=deal.organisation_id,
        incoterm=Incoterm.CIF,
        incoterm_place="Hamburg, Germany",
        status=QuoteStatus.APPROVED,
        total_quote_price=Decimal("78200.00"),
    )

    rules = get_rule_definitions_for_deal(deal, active_quote)
    rule_codes = [r["rule_code"] for r in rules]

    assert "SBP_E_FORM_E" in rule_codes
    assert "SBP_PROCEEDS_120D" in rule_codes
    assert "INCOTERM_CIF_INSURANCE" in rule_codes
    assert "EU_REX_GSP_PLUS" in rule_codes
    assert "REACH_CHEMICAL_CONFORMITY" in rule_codes
    assert "UCP600_LC_COMPLIANCE" in rule_codes
    assert "COMMERCIAL_INVOICE_FINAL" in rule_codes
    assert "PACKING_LIST_VERIFICATION" in rule_codes


def test_compliance_rules_for_us_fob_advance_payment():
    """
    Test scenario:
    Lahore exporter sending Denim Jeans to USA under FOB Karachi with Advance TT.
    Expected rules:
      1. SBP Electronic Form-E
      2. SBP Advance Payment Realization (Form-R)
      3. US CBP Importer Security Filing (ISF 10+2)
      4. Textile Care Labeling Declaration
      5. Buyer Nominated Forwarder Routing Order
    """
    deal = Deal(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        reference="DEAL-2026-002",
        buyer_name="New York Apparel LLC",
        state=DealState.INQUIRY,
        notes="Destination: New York, United States. Payment: 100% Advance Wire Transfer (TT)",
    )
    product = Product(
        id=uuid.uuid4(),
        organisation_id=deal.organisation_id,
        sku="DNM-JNS-01",
        name="Men's Cotton Denim Jeans",
        unit_of_measure="PCS",
    )
    deal.line_items = [
        DealLineItem(
            id=uuid.uuid4(),
            deal_id=deal.id,
            product_id=product.id,
            quantity=Decimal("3000"),
            product=product,
        )
    ]
    active_quote = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal.id,
        organisation_id=deal.organisation_id,
        incoterm=Incoterm.FOB,
        incoterm_place="Karachi Port, Pakistan",
        status=QuoteStatus.APPROVED,
        total_quote_price=Decimal("45000.00"),
    )

    rules = get_rule_definitions_for_deal(deal, active_quote)
    rule_codes = [r["rule_code"] for r in rules]

    assert "SBP_E_FORM_E" in rule_codes
    assert "SBP_ADVANCE_REALIZATION" in rule_codes
    assert "US_CBP_ISF_FILING" in rule_codes
    assert "TEXTILE_FIBER_COMPOSITION" in rule_codes
    assert "INCOTERM_FOB_FORWARDER_NOTICE" in rule_codes


def test_hs_code_pct_taxonomy_matching():
    """Verify standard Pakistan Customs Tariff classification matching."""
    # Match Footballs
    fb_match = match_pct_taxonomy("Size-5 FIFA Quality Match Football FB-S5")
    assert fb_match is not None
    assert fb_match["code"] == "9506.6210"
    assert "Inflatable balls" in fb_match["heading"]

    # Match Surgical Scissors
    surg_match = match_pct_taxonomy("Metzenbaum Stainless Steel Surgical Scissors 7 inch")
    assert surg_match is not None
    assert surg_match["code"] == "9018.9010"

    # Match Basmati Rice
    rice_match = match_pct_taxonomy("Super Kernel Basmati Rice 1121 Parboiled 25kg")
    assert rice_match is not None
    assert rice_match["code"] == "1006.3010"

    # Match Cotton T-Shirts
    tshirt_match = match_pct_taxonomy("100% Ring Spun Cotton Round Neck T-Shirt")
    assert tshirt_match is not None
    assert tshirt_match["code"] == "6109.1000"


def test_sbp_regulation_query_engine():
    """Verify grounded SBP trade regulation citations and effective dates."""
    res = query_sbp_regulations("What is the deadline for receiving payment after export shipment?")
    assert len(res["citations"]) > 0
    assert "120" in res["answer"] or "120" in res["citations"][0]["verbatim_text"]
    assert res["authority"] == "State Bank of Pakistan (SBP)"
    assert "Informational advisory only" in res["disclaimer"]

    # Query EU REX System
    rex_res = query_sbp_regulations(
        "How does EU GSP+ origin work for Germany exports?",
        destination_country="Germany",
    )
    assert len(rex_res["citations"]) > 0
    assert any("REX" in c["section_or_circular"] or "GSP" in c["section_or_circular"] for c in rex_res["citations"])
