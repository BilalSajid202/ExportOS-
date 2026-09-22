"""
ExportOS — Unit & Integration Tests for Phase 15 (Executive Analytics & Dashboard)
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.deal import Deal, DealState, DealLineItem
from app.models.product import Product
from app.models.costing import DealQuote, QuoteStatus, Incoterm
from app.models.documents import DocumentSet, DocumentStatus
from app.models.logistics import Shipment, PaymentTransaction, PaymentStatus
from app.services.analytics import (
    get_executive_kpis,
    get_profitability_by_incoterm,
    get_profitability_by_product,
    get_destination_markets,
    get_sbp_realization_exposure,
    get_full_executive_analytics,
)


class MockQuery:
    def __init__(self, data):
        self.data = data if isinstance(data, list) else ([data] if data is not None else [])

    def filter(self, *args, **kwargs):
        filtered = self.data
        for arg in args:
            if hasattr(arg, 'left') and hasattr(arg, 'right'):
                col_name = arg.left.name if hasattr(arg.left, 'name') else str(arg.left).split('.')[-1]
                target_val = getattr(arg.right, 'value', getattr(arg.right, 'val', None))
                if target_val is not None:
                    filtered = [item for item in filtered if getattr(item, col_name, None) == target_val]
        return MockQuery(filtered)

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self.data

    def first(self):
        return self.data[0] if self.data else None


@pytest.mark.asyncio
async def test_executive_kpis_calculation():
    """Verify aggregated pipeline value, realized payments, and margin percentages."""
    org_id = uuid.uuid4()
    deal_1 = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-01", buyer_name="Buyer Alpha", state=DealState.QUOTED)
    deal_2 = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-02", buyer_name="Buyer Beta", state=DealState.CLOSED)

    quote_1 = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal_1.id,
        organisation_id=org_id,
        incoterm=Incoterm.CIF,
        incoterm_place="Hamburg, Germany",
        total_quote_price=Decimal("50000.00"),
        margin_percentage=Decimal("18.0"),
    )
    quote_2 = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal_2.id,
        organisation_id=org_id,
        incoterm=Incoterm.FOB,
        incoterm_place="Karachi Port",
        total_quote_price=Decimal("30000.00"),
        margin_percentage=Decimal("12.0"),
    )

    payment_1 = PaymentTransaction(
        id=uuid.uuid4(),
        deal_id=deal_2.id,
        organisation_id=org_id,
        amount=Decimal("30000.00"),
        settlement_amount_pkr=Decimal("8400000.00"),
    )

    doc_set = DocumentSet(
        id=uuid.uuid4(),
        deal_id=deal_2.id,
        organisation_id=org_id,
        status=DocumentStatus.APPROVED,
    )

    class MockSession:
        def query(self, model):
            if model == Deal:
                return MockQuery([deal_1, deal_2])
            if model == DealQuote:
                return MockQuery([quote_1, quote_2])
            if model == PaymentTransaction:
                return MockQuery([payment_1])
            if model == DocumentSet:
                return MockQuery([doc_set])
            if model == Shipment:
                return MockQuery([])
            if model == Product:
                return MockQuery([])
            return MockQuery([])

    mock_db = MockSession()
    kpis = await get_executive_kpis(org_id, mock_db)

    assert kpis.total_pipeline_value_usd == Decimal("80000.00")
    assert kpis.total_realized_revenue_usd == Decimal("30000.00")
    assert kpis.total_realized_revenue_pkr == Decimal("8400000.00")
    assert kpis.average_gross_margin_pct == Decimal("15.0")
    assert kpis.total_active_deals == 1
    assert kpis.total_completed_deals == 1
    assert kpis.doc_consistency_pass_rate_pct == Decimal("100.0")


@pytest.mark.asyncio
async def test_profitability_by_incoterm_aggregation():
    """Verify grouping and margin computation per Incoterm."""
    org_id = uuid.uuid4()
    q_cif = DealQuote(
        deal_id=uuid.uuid4(),
        organisation_id=org_id,
        incoterm=Incoterm.CIF,
        incoterm_place="Rotterdam",
        total_quote_price=Decimal("100000.00"),
        total_cost=Decimal("80000.00"),
        margin_amount=Decimal("20000.00"),
        margin_percentage=Decimal("20.0"),
    )
    q_fob = DealQuote(
        deal_id=uuid.uuid4(),
        organisation_id=org_id,
        incoterm=Incoterm.FOB,
        incoterm_place="Karachi Port",
        total_quote_price=Decimal("40000.00"),
        total_cost=Decimal("35000.00"),
        margin_amount=Decimal("5000.00"),
        margin_percentage=Decimal("12.5"),
    )

    class MockSession:
        def query(self, model):
            if model == DealQuote:
                return MockQuery([q_cif, q_fob])
            return MockQuery([])

    mock_db = MockSession()
    incoterm_stats = await get_profitability_by_incoterm(org_id, mock_db)

    assert len(incoterm_stats) == 2
    cif_stat = next(s for s in incoterm_stats if s.incoterm == "CIF")
    assert cif_stat.total_revenue_usd == Decimal("100000.00")
    assert cif_stat.total_margin_usd == Decimal("20000.00")
    assert cif_stat.average_margin_pct == Decimal("20.0")


@pytest.mark.asyncio
async def test_sbp_120_day_realization_exposure_buckets():
    """Verify aging calculation against SBP Chapter XII 120-day limit."""
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Deal A: Dispatched 10 days ago (Safe: 110 days left)
    deal_a = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-SAFE", buyer_name="Buyer A", state=DealState.SHIPPED, created_at=now - timedelta(days=10))
    quote_a = DealQuote(deal_id=deal_a.id, total_quote_price=Decimal("25000.00"))
    shipment_a = Shipment(deal_id=deal_a.id, atd=now - timedelta(days=10))

    # Deal B: Dispatched 105 days ago (Critical: 15 days left)
    deal_b = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-WARN", buyer_name="Buyer B", state=DealState.SHIPPED, created_at=now - timedelta(days=105))
    quote_b = DealQuote(deal_id=deal_b.id, total_quote_price=Decimal("45000.00"))
    shipment_b = Shipment(deal_id=deal_b.id, atd=now - timedelta(days=105))

    # Deal C: Dispatched 135 days ago (Overdue Violation: -15 days left)
    deal_c = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-OVERDUE", buyer_name="Buyer C", state=DealState.SHIPPED, created_at=now - timedelta(days=135))
    quote_c = DealQuote(deal_id=deal_c.id, total_quote_price=Decimal("60000.00"))
    shipment_c = Shipment(deal_id=deal_c.id, atd=now - timedelta(days=135))

    class MockSession:
        def query(self, model):
            if model == Deal:
                return MockQuery([deal_a, deal_b, deal_c])
            if model == DealQuote:
                return MockQuery([quote_a, quote_b, quote_c])
            if model == Shipment:
                return MockQuery([shipment_a, shipment_b, shipment_c])
            if model == PaymentTransaction:
                return MockQuery([])  # 0 payments -> all full balance due
            return MockQuery([])

    mock_db = MockSession()
    sbp_report = await get_sbp_realization_exposure(org_id, mock_db)

    assert sbp_report.total_outstanding_usd == Decimal("130000.00")
    assert sbp_report.current_bucket_usd == Decimal("25000.00")
    assert sbp_report.aging_91_120_sbp_warning_usd == Decimal("45000.00")
    assert sbp_report.overdue_120_plus_violation_usd == Decimal("60000.00")
    assert sbp_report.at_risk_deals_count == 2


@pytest.mark.asyncio
async def test_profitability_by_product_calculation():
    """Verify units sold and revenue contribution per product SKU."""
    org_id = uuid.uuid4()
    prod = Product(
        id=uuid.uuid4(),
        organisation_id=org_id,
        name="Match Quality Leather Football",
        sku="FB-LTH-01",
        base_cost=Decimal("20.00"),
    )
    deal = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-FB-01", buyer_name="Sports Direct")
    line_item = DealLineItem(
        id=uuid.uuid4(),
        organisation_id=org_id,
        deal_id=deal.id,
        product_id=prod.id,
        quantity=Decimal("500"),
    )
    quote = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal.id,
        organisation_id=org_id,
        base_cost=Decimal("20.00"),
        unit_price=Decimal("25.00"),
        total_quote_price=Decimal("12500.00"),
        total_cost=Decimal("10000.00"),
    )

    class MockSession:
        def query(self, model):
            if model == Product:
                return MockQuery([prod])
            if model == DealLineItem:
                return MockQuery([line_item])
            if model == DealQuote:
                return MockQuery([quote])
            if model == Deal:
                return MockQuery([deal])
            return MockQuery([])

    mock_db = MockSession()
    product_stats = await get_profitability_by_product(org_id, mock_db)

    assert len(product_stats) == 1
    assert product_stats[0].sku == "FB-LTH-01"
    assert product_stats[0].units_sold == Decimal("500.00")
    assert product_stats[0].total_revenue_usd == Decimal("12500.00")
    assert product_stats[0].total_cost_usd == Decimal("10000.00")
    assert product_stats[0].gross_margin_pct == Decimal("20.0")


@pytest.mark.asyncio
async def test_full_executive_analytics_integration():
    """Verify get_full_executive_analytics bundles all sub-reports without error."""
    org_id = uuid.uuid4()
    deal = Deal(id=uuid.uuid4(), organisation_id=org_id, reference="EXP-ALL", buyer_name="Global Trade BV", state=DealState.QUOTED)
    quote = DealQuote(
        id=uuid.uuid4(),
        deal_id=deal.id,
        organisation_id=org_id,
        incoterm=Incoterm.FOB,
        incoterm_place="Karachi Port",
        total_quote_price=Decimal("50000.00"),
        total_cost=Decimal("40000.00"),
        margin_percentage=Decimal("20.0"),
        unit_price=Decimal("50.00"),
        base_cost=Decimal("40.00"),
    )
    prod = Product(id=uuid.uuid4(), organisation_id=org_id, name="Cricket Bat", sku="CRK-01", base_cost=Decimal("40.00"))

    class MockSession:
        def query(self, model):
            if model == Deal:
                return MockQuery([deal])
            if model == DealQuote:
                return MockQuery([quote])
            if model == Product:
                return MockQuery([prod])
            if model == DocumentSet:
                return MockQuery([])
            if model == PaymentTransaction:
                return MockQuery([])
            if model == Shipment:
                return MockQuery([])
            if model == DealLineItem:
                return MockQuery([])
            return MockQuery([])

    mock_db = MockSession()
    res = await get_full_executive_analytics(org_id, mock_db)

    assert res.kpis.total_pipeline_value_usd == Decimal("50000.00")
    assert len(res.profitability_by_incoterm) == 1
    assert len(res.profitability_by_product) == 1
    assert len(res.destination_markets) == 1
    assert len(res.pipeline_funnel) == 1
    assert res.sbp_exposure.total_outstanding_usd == Decimal("50000.00")

