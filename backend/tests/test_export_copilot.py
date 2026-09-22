"""
ExportOS — Unit & Integration Tests for Export Copilot & Qdrant RAG (Phase 14)
"""

from decimal import Decimal
import uuid
import pytest

from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.deal import Deal, DealLineItem, DealState
from app.models.costing import DealQuote, Incoterm, QuoteStatus
from app.models.documents import DocumentSet, GeneratedDocument, DocumentType, DocumentStatus
from app.models.compliance import ComplianceCheck, ComplianceCategory, ComplianceStatus
from app.models.logistics import Shipment, ShipmentStatus, TransportMode, PaymentTransaction, PaymentType
from app.models.inventory import InventoryReservation, ReservationStatus
from app.services.vector_pipeline import (
    sync_docs_folder_to_qdrant,
    query_qdrant_vectors,
    generate_dense_embedding,
    chunk_markdown_file,
)
from app.services.copilot import (
    inspect_deal_readiness,
    draft_buyer_correspondence,
)


def test_dense_embedding_generation():
    """Verify deterministic normalized 384-dimensional vector embedding."""
    vec1 = generate_dense_embedding("State Bank of Pakistan 120-Day Export Realization")
    assert len(vec1) == 384
    # Check norm is ~ 1.0
    norm = sum(x * x for x in vec1) ** 0.5
    assert abs(norm - 1.0) < 1e-4

    vec2 = generate_dense_embedding("State Bank of Pakistan 120-Day Export Realization")
    assert vec1 == vec2  # Deterministic consistency


def test_docs_folder_ingestion_and_qdrant_search():
    """Verify loading markdown knowledge docs from data/docs and querying vectors."""
    indexed_count = sync_docs_folder_to_qdrant()
    assert indexed_count > 0

    # Query for SBP 120-day realization rules
    results = query_qdrant_vectors("What is the deadline for SBP foreign exchange realization?", top_k=3)
    assert len(results) > 0
    assert any("sbp" in r["source"].lower() or "120" in r["text"] for r in results)


@pytest.mark.asyncio
async def test_readiness_inspector_detects_blockers():
    """
    Test scenario: Incomplete deal without inventory reservation, missing documents,
    and pending mandatory compliance checks.
    Inspector must flag overall_status as NOT_READY or ACTION_REQUIRED with explicit blockers.
    """
    deal = Deal(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        reference="EXP-2026-BLOCK-01",
        buyer_name="European Retailers BV",
        state=DealState.INQUIRY,
        notes="FOB Karachi inquiry",
    )
    product = Product(
        id=uuid.uuid4(),
        organisation_id=deal.organisation_id,
        name="Leather Driving Gloves",
        sku="GLV-LTH-01",
    )
    line_item = DealLineItem(
        id=uuid.uuid4(),
        deal_id=deal.id,
        product_id=product.id,
        quantity=Decimal("2000"),
        product=product,
    )
    deal.line_items = [line_item]

    # Mock DB session object to simulate inspect_deal_readiness query responses
    class MockQuery:
        def __init__(self, data):
            self.data = data
        def filter(self, *args, **kwargs):
            return self
        def all(self):
            return self.data
        def first(self):
            return self.data[0] if self.data else None
        def order_by(self, *args, **kwargs):
            return self

    class MockSession:
        def query(self, model):
            if model == Deal:
                return MockQuery([deal])
            if model == InventoryReservation:
                return MockQuery([])  # 0 inventory reserved -> BLOCKED
            if model == DealQuote:
                return MockQuery([])  # 0 quote -> BLOCKED
            if model == DocumentSet:
                return MockQuery([])  # 0 documents -> BLOCKED
            if model == ComplianceCheck:
                return MockQuery([
                    ComplianceCheck(
                        id=uuid.uuid4(),
                        deal_id=deal.id,
                        title="SBP Electronic Form-E",
                        is_mandatory=True,
                        status=ComplianceStatus.NOT_STARTED,  # NOT_STARTED -> BLOCKED
                    )
                ])
            if model == Shipment:
                return MockQuery([])
            if model == PaymentTransaction:
                return MockQuery([])
            return MockQuery([])

    mock_db = MockSession()
    readiness = await inspect_deal_readiness(deal.id, mock_db)

    assert readiness.is_ready_to_ship is False
    assert readiness.overall_status in ["ACTION_REQUIRED", "NOT_READY"]
    assert len(readiness.blockers) >= 3  # Inventory, Quote, Docs, Compliance blockers
    assert readiness.score_percentage < 50


@pytest.mark.asyncio
async def test_buyer_correspondence_drafting():
    """Verify commercial email drafting with deal parameters."""
    deal_id = uuid.uuid4()
    org_id = uuid.uuid4()

    deal = Deal(
        id=deal_id,
        organisation_id=org_id,
        reference="EXP-2026-GER-99",
        buyer_name="Munich Sports GmbH",
    )
    quote = DealQuote(
        deal_id=deal_id,
        incoterm=Incoterm.CIF,
        incoterm_place="Hamburg, Germany",
        total_quote_price=Decimal("85000.00"),
        currency="USD",
    )

    class MockQuery:
        def __init__(self, item):
            self.item = item
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def first(self):
            return self.item
        def all(self):
            return [self.item] if self.item else []

    class MockSession:
        def query(self, model):
            if model == Deal:
                return MockQuery(deal)
            if model == DealQuote:
                return MockQuery(quote)
            return MockQuery(None)

    mock_db = MockSession()

    # 1. Test Order Confirmation draft
    order_draft = await draft_buyer_correspondence("ORDER_CONFIRMATION", deal_id, org_id, mock_db)
    assert "EXP-2026-GER-99" in order_draft.subject
    assert "Munich Sports GmbH" in order_draft.body
    assert "USD 85,000.00" in order_draft.body
    assert order_draft.human_approval_required is True

    # 2. Test SBP Payment Reminder draft
    pay_draft = await draft_buyer_correspondence("PAYMENT_REMINDER_SBP", deal_id, org_id, mock_db)
    assert "State Bank of Pakistan (SBP) Foreign Exchange Manual Chapter XII" in pay_draft.body
    assert "Electronic Form-E" in pay_draft.body
