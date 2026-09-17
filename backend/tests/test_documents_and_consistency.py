"""
ExportOS — Unit & Service Tests for Document Generation & Consistency Checker (Phases 10 & 11)
"""

from decimal import Decimal
import pytest

from app.models.documents import (
    DocumentSet,
    DocumentStatus,
    DocumentType,
    GeneratedDocument,
)
from app.services.consistency_checker import check_document_set_consistency
from app.services.document_generator import compute_sha256, render_document_html


def test_sha256_hash_integrity():
    """Verify cryptographic SHA-256 hash generation is reproducible and sensitive to edits."""
    doc_data = {
        "document_number": "CI-2026-0001-R1",
        "total_amount": 78200.00,
        "currency": "USD",
        "items": [{"sku": "SG-FB-M5-001", "quantity": 5000}],
    }
    hash1 = compute_sha256(doc_data)
    hash2 = compute_sha256(doc_data)
    assert hash1 == hash2
    assert len(hash1) == 64

    # Any minor change must produce completely different hash
    edited_data = dict(doc_data)
    edited_data["total_amount"] = 78200.01
    hash3 = compute_sha256(edited_data)
    assert hash1 != hash3


def test_cross_document_consistency_pass():
    """Verify consistency checker passes with 100% score when documents match perfectly."""
    shared_buyer = "Sportland Germany GmbH"
    shared_incoterm = "CIF"
    shared_place = "Hamburg, Germany"
    shared_qty = 5000.0
    shared_total = 78200.00
    shared_curr = "USD"

    # Mock Proforma Invoice
    pi = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.PROFORMA_INVOICE,
        document_number="PI-001",
        title="Proforma Invoice",
        content_json={
            "buyer": {"name": shared_buyer},
            "commercial_terms": {"incoterm": shared_incoterm, "incoterm_place": shared_place},
            "financial_summary": {"total_quantity": shared_qty, "total_amount": shared_total, "currency": shared_curr},
        },
        sha256_hash="abc",
    )

    # Mock Commercial Invoice
    ci = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.COMMERCIAL_INVOICE,
        document_number="CI-001",
        title="Commercial Invoice",
        content_json={
            "consignee": {"name": shared_buyer},
            "shipping_details": {"incoterm": shared_incoterm, "incoterm_place": shared_place},
            "financial_summary": {"total_quantity": shared_qty, "total_amount": shared_total, "currency": shared_curr},
            "line_items": [{"sku": "SG-FB-M5-001", "hs_code": "9506.62.10"}],
        },
        sha256_hash="def",
    )

    # Mock Packing List
    pl = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.PACKING_LIST,
        document_number="PL-001",
        title="Packing List",
        content_json={
            "consignee": {"name": shared_buyer},
            "packaging_summary": {
                "total_quantity": shared_qty,
                "total_net_weight_kg": 2175.0,
                "total_gross_weight_kg": 2392.5,
                "total_packages_cartons": 200,
            },
        },
        sha256_hash="ghi",
    )

    # Mock Certificate of Origin
    coo = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.CERTIFICATE_OF_ORIGIN,
        document_number="COO-001",
        title="Certificate of Origin",
        content_json={
            "consignee": {"name": shared_buyer},
            "items": [{"description": "Size-5 Football", "hs_code": "9506.62.10"}],
        },
        sha256_hash="jkl",
    )

    doc_set = DocumentSet(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        revision_number=1,
    )
    doc_set.documents = [pi, ci, pl, coo]

    result = check_document_set_consistency(doc_set)
    assert result.is_consistent is True
    assert result.score == 100
    assert len(result.discrepancies) == 0


def test_cross_document_consistency_discrepancy_detection():
    """Verify consistency checker detects quantity and price mismatches between PI and CI."""
    pi = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.PROFORMA_INVOICE,
        document_number="PI-001",
        title="Proforma Invoice",
        content_json={
            "buyer": {"name": "Sportland Germany GmbH"},
            "commercial_terms": {"incoterm": "CIF", "incoterm_place": "Hamburg, Germany"},
            "financial_summary": {"total_quantity": 5000.0, "total_amount": 78200.00, "currency": "USD"},
        },
        sha256_hash="abc",
    )

    # Discrepancy: CI has 4,800 quantity instead of 5,000!
    ci = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.COMMERCIAL_INVOICE,
        document_number="CI-001",
        title="Commercial Invoice",
        content_json={
            "consignee": {"name": "Sportland Germany GmbH"},
            "shipping_details": {"incoterm": "CIF", "incoterm_place": "Hamburg, Germany"},
            "financial_summary": {"total_quantity": 4800.0, "total_amount": 75000.00, "currency": "USD"},
            "line_items": [{"sku": "SG-FB-M5-001", "hs_code": "9506.62.10"}],
        },
        sha256_hash="def",
    )

    pl = GeneratedDocument(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        document_set_id="00000000-0000-0000-0000-000000000003",
        doc_type=DocumentType.PACKING_LIST,
        document_number="PL-001",
        title="Packing List",
        content_json={
            "consignee": {"name": "Sportland Germany GmbH"},
            "packaging_summary": {
                "total_quantity": 5000.0,
                "total_net_weight_kg": 2175.0,
                "total_gross_weight_kg": 2392.5,
                "total_packages_cartons": 200,
            },
        },
        sha256_hash="ghi",
    )

    doc_set = DocumentSet(
        organisation_id="00000000-0000-0000-0000-000000000001",
        deal_id="00000000-0000-0000-0000-000000000002",
        revision_number=1,
    )
    doc_set.documents = [pi, ci, pl]

    result = check_document_set_consistency(doc_set)
    assert result.is_consistent is False
    assert result.score < 100
    assert len(result.discrepancies) >= 2
    assert any("Quantity mismatch" in d for d in result.discrepancies)
    assert any("Financial total discrepancy" in d for d in result.discrepancies)
