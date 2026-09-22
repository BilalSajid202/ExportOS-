"""
Tradeloop — Executive Analytics & Profitability Engine (Phase 15)

Deterministic calculations for financial KPI summaries, Incoterm/SKU profitability,
SBP Chapter XII FX realization exposure, and pipeline velocity.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal, DealState, DealLineItem
from app.models.product import Product
from app.models.costing import DealQuote, QuoteStatus
from app.models.documents import DocumentSet, DocumentStatus
from app.models.compliance import ComplianceCheck, ComplianceStatus
from app.models.logistics import Shipment, ShipmentStatus, PaymentTransaction, PaymentStatus
from app.schemas.analytics import (
    ExecutiveKPISummary,
    ProfitabilityByIncoterm,
    ProfitabilityByProduct,
    DestinationMarketAnalytics,
    DealStateDistribution,
    SBPExposureDealItem,
    SBPRealizationExposureReport,
    ExecutiveAnalyticsResponse,
)


async def _get_all(db: Any, stmt: Any, model: Any, filter_fn=None) -> List[Any]:
    if isinstance(db, AsyncSession) or (hasattr(db, "execute") and not hasattr(db, "query")):
        res = await db.execute(stmt)
        return list(res.scalars().all())
    elif hasattr(db, "query"):
        q = db.query(model)
        if filter_fn:
            q = filter_fn(q)
        return list(q.all())
    return []


async def _get_first(db: Any, stmt: Any, model: Any, filter_fn=None) -> Optional[Any]:
    if isinstance(db, AsyncSession) or (hasattr(db, "execute") and not hasattr(db, "query")):
        res = await db.execute(stmt)
        return res.scalars().first()
    elif hasattr(db, "query"):
        q = db.query(model)
        if filter_fn:
            q = filter_fn(q)
        return q.first()
    return None


async def get_executive_kpis(organisation_id: UUID, db: Any) -> ExecutiveKPISummary:
    """Calculates top-line executive KPIs across all deals for the organization."""
    stmt = select(Deal).where(Deal.organisation_id == organisation_id)
    deals = await _get_all(db, stmt, Deal, lambda q: q.filter(Deal.organisation_id == organisation_id))
    
    total_pipeline_val = Decimal("0.00")
    total_realized_usd = Decimal("0.00")
    total_realized_pkr = Decimal("0.00")
    margin_sum = Decimal("0.00")
    quote_count = 0
    active_count = 0
    completed_count = 0

    for deal in deals:
        if deal.state == DealState.CANCELLED:
            continue
        elif deal.state in (DealState.PAID, DealState.CLOSED):
            completed_count += 1
        else:
            active_count += 1

        # Check quotes for pipeline value & margin
        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        latest_quote = await _get_first(
            db, q_stmt, DealQuote, lambda q: q.filter(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        )
        if latest_quote:
            total_pipeline_val += Decimal(str(latest_quote.total_quote_price or "0.00"))
            margin_sum += Decimal(str(latest_quote.margin_percentage or "0.00"))
            quote_count += 1

        # Check realized payments
        p_stmt = select(PaymentTransaction).where(PaymentTransaction.deal_id == deal.id)
        payments = await _get_all(db, p_stmt, PaymentTransaction, lambda q: q.filter(PaymentTransaction.deal_id == deal.id))
        for p in payments:
            total_realized_usd += Decimal(str(p.amount or "0.00"))
            total_realized_pkr += Decimal(str(p.settlement_amount_pkr or "0.00"))

    # SBP At-risk exposure calculation
    sbp_report = await get_sbp_realization_exposure(organisation_id, db)
    at_risk_sbp = sbp_report.aging_91_120_sbp_warning_usd + sbp_report.overdue_120_plus_violation_usd

    # Document consistency pass rate
    d_stmt = select(DocumentSet).where(DocumentSet.organisation_id == organisation_id)
    doc_sets = await _get_all(db, d_stmt, DocumentSet, lambda q: q.filter(DocumentSet.organisation_id == organisation_id))
    passed_docs = [ds for ds in doc_sets if ds.status == DocumentStatus.APPROVED]
    doc_pass_rate = (
        (Decimal(len(passed_docs)) / Decimal(len(doc_sets)) * Decimal("100.00"))
        if doc_sets
        else Decimal("100.00")
    )

    avg_margin = (margin_sum / Decimal(quote_count)) if quote_count > 0 else Decimal("0.00")

    return ExecutiveKPISummary(
        total_pipeline_value_usd=total_pipeline_val.quantize(Decimal("0.01")),
        total_realized_revenue_usd=total_realized_usd.quantize(Decimal("0.01")),
        total_realized_revenue_pkr=total_realized_pkr.quantize(Decimal("0.01")),
        average_gross_margin_pct=avg_margin.quantize(Decimal("0.1")),
        total_active_deals=active_count,
        total_completed_deals=completed_count,
        sbp_at_risk_exposure_usd=at_risk_sbp.quantize(Decimal("0.01")),
        doc_consistency_pass_rate_pct=doc_pass_rate.quantize(Decimal("0.1")),
    )


async def get_profitability_by_incoterm(organisation_id: UUID, db: Any) -> List[ProfitabilityByIncoterm]:
    """Aggregates revenue, cost, and gross margin grouped by Incoterm."""
    stmt = select(DealQuote).where(DealQuote.organisation_id == organisation_id)
    quotes = await _get_all(db, stmt, DealQuote, lambda q: q.filter(DealQuote.organisation_id == organisation_id))

    grouped: Dict[str, Dict[str, Any]] = {}

    for q in quotes:
        incoterm_name = q.incoterm.value if hasattr(q.incoterm, "value") else str(q.incoterm)
        if incoterm_name not in grouped:
            grouped[incoterm_name] = {
                "deal_count": 0,
                "total_revenue": Decimal("0.00"),
                "total_cost": Decimal("0.00"),
                "total_margin": Decimal("0.00"),
                "margin_percentages": [],
            }

        grouped[incoterm_name]["deal_count"] += 1
        grouped[incoterm_name]["total_revenue"] += Decimal(str(q.total_quote_price or "0.00"))
        grouped[incoterm_name]["total_cost"] += Decimal(str(q.total_cost or "0.00"))
        grouped[incoterm_name]["total_margin"] += Decimal(str(q.margin_amount or "0.00"))
        grouped[incoterm_name]["margin_percentages"].append(Decimal(str(q.margin_percentage or "0.00")))

    results = []
    for incoterm, data in grouped.items():
        avg_pct = (
            sum(data["margin_percentages"]) / Decimal(len(data["margin_percentages"]))
            if data["margin_percentages"]
            else Decimal("0.00")
        )
        results.append(
            ProfitabilityByIncoterm(
                incoterm=incoterm,
                deal_count=data["deal_count"],
                total_revenue_usd=data["total_revenue"].quantize(Decimal("0.01")),
                total_cost_usd=data["total_cost"].quantize(Decimal("0.01")),
                total_margin_usd=data["total_margin"].quantize(Decimal("0.01")),
                average_margin_pct=avg_pct.quantize(Decimal("0.1")),
            )
        )

    return sorted(results, key=lambda x: x.total_revenue_usd, reverse=True)


async def get_profitability_by_product(organisation_id: UUID, db: Any) -> List[ProfitabilityByProduct]:
    """Computes units sold and revenue contribution per product SKU."""
    stmt = select(Product).where(Product.organisation_id == organisation_id)
    products = await _get_all(db, stmt, Product, lambda q: q.filter(Product.organisation_id == organisation_id))
    results = []

    for product in products:
        item_stmt = (
            select(DealLineItem)
            .join(Deal, Deal.id == DealLineItem.deal_id)
            .where(DealLineItem.product_id == product.id, Deal.organisation_id == organisation_id)
        )
        line_items = await _get_all(
            db, item_stmt, DealLineItem,
            lambda q: q.join(Deal, Deal.id == DealLineItem.deal_id).filter(
                DealLineItem.product_id == product.id, Deal.organisation_id == organisation_id
            )
        )

        total_units = Decimal("0.00")
        total_rev = Decimal("0.00")
        total_cost = Decimal("0.00")

        base_unit_cost = Decimal(str(product.base_cost or "25.00"))
        base_unit_price = base_unit_cost * Decimal("1.25") if base_unit_cost > 0 else Decimal("30.00")

        for item in line_items:
            qty = Decimal(str(item.quantity or "0.00"))
            total_units += qty
            
            # Check if associated deal has a quote
            q_stmt = select(DealQuote).where(DealQuote.deal_id == item.deal_id).order_by(desc(DealQuote.created_at))
            quote = await _get_first(
                db, q_stmt, DealQuote, lambda q: q.filter(DealQuote.deal_id == item.deal_id).order_by(desc(DealQuote.created_at))
            )
            if quote and quote.unit_price and quote.unit_price > 0:
                item_price = Decimal(str(quote.unit_price))
                item_cost = Decimal(str(quote.base_cost or base_unit_cost))
                total_rev += qty * item_price
                total_cost += qty * item_cost
            else:
                total_rev += qty * base_unit_price
                total_cost += qty * base_unit_cost

        margin_pct = (
            ((total_rev - total_cost) / total_rev * Decimal("100.00"))
            if total_rev > 0
            else Decimal("20.00")
        )

        results.append(
            ProfitabilityByProduct(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                units_sold=total_units.quantize(Decimal("0.01")),
                total_revenue_usd=total_rev.quantize(Decimal("0.01")),
                total_cost_usd=total_cost.quantize(Decimal("0.01")),
                gross_margin_pct=margin_pct.quantize(Decimal("0.1")),
            )
        )

    return sorted(results, key=lambda x: x.total_revenue_usd, reverse=True)


async def get_destination_markets(organisation_id: UUID, db: Any) -> List[DestinationMarketAnalytics]:
    """Analyzes export pipeline values across destination buyer countries."""
    stmt = select(Deal).where(Deal.organisation_id == organisation_id)
    deals = await _get_all(db, stmt, Deal, lambda q: q.filter(Deal.organisation_id == organisation_id))
    total_pipeline = Decimal("0.00")
    grouped: Dict[str, Dict[str, Any]] = {}

    for deal in deals:
        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        latest_quote = await _get_first(
            db, q_stmt, DealQuote, lambda q: q.filter(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        )
        deal_val = Decimal(str(latest_quote.total_quote_price or "0.00")) if latest_quote else Decimal("0.00")
        total_pipeline += deal_val

        # Infer country from incoterm_place, notes, or buyer name
        place = latest_quote.incoterm_place if latest_quote else (deal.notes or "International")
        country = "International"
        for candidate in ["Germany", "United Kingdom", "United States", "Netherlands", "UAE", "France", "Italy", "Spain", "Saudi Arabia", "Canada"]:
            if candidate.lower() in place.lower() or candidate.lower() in (deal.buyer_name or "").lower():
                country = candidate
                break

        if country not in grouped:
            grouped[country] = {"deal_count": 0, "buyers": set(), "total_val": Decimal("0.00")}

        grouped[country]["deal_count"] += 1
        grouped[country]["buyers"].add(deal.buyer_name)
        grouped[country]["total_val"] += deal_val

    results = []
    for country, data in grouped.items():
        pct = (
            (data["total_val"] / total_pipeline * Decimal("100.00"))
            if total_pipeline > 0
            else Decimal("0.00")
        )
        results.append(
            DestinationMarketAnalytics(
                destination_country=country,
                deal_count=data["deal_count"],
                buyer_count=len(data["buyers"]),
                total_value_usd=data["total_val"].quantize(Decimal("0.01")),
                percentage_of_pipeline=pct.quantize(Decimal("0.1")),
            )
        )

    return sorted(results, key=lambda x: x.total_value_usd, reverse=True)


async def get_pipeline_funnel(organisation_id: UUID, db: Any) -> List[DealStateDistribution]:
    """Computes distribution of deals and dollar volume across state machine."""
    stmt = select(Deal).where(Deal.organisation_id == organisation_id)
    deals = await _get_all(db, stmt, Deal, lambda q: q.filter(Deal.organisation_id == organisation_id))
    grouped: Dict[str, Dict[str, Any]] = {}

    for deal in deals:
        state_name = deal.state.value if hasattr(deal.state, "value") else str(deal.state)
        if state_name not in grouped:
            grouped[state_name] = {"count": 0, "val": Decimal("0.00")}

        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        latest_quote = await _get_first(
            db, q_stmt, DealQuote, lambda q: q.filter(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        )
        deal_val = Decimal(str(latest_quote.total_quote_price or "0.00")) if latest_quote else Decimal("0.00")

        grouped[state_name]["count"] += 1
        grouped[state_name]["val"] += deal_val

    results = []
    for state, data in grouped.items():
        results.append(
            DealStateDistribution(
                state=state,
                deal_count=data["count"],
                total_value_usd=data["val"].quantize(Decimal("0.01")),
            )
        )

    return results


async def get_sbp_realization_exposure(organisation_id: UUID, db: Any) -> SBPRealizationExposureReport:
    """
    Evaluates receivables aging against State Bank of Pakistan Foreign Exchange Manual Chapter XII
    120-day realization deadline.
    """
    stmt = select(Deal).where(Deal.organisation_id == organisation_id)
    deals = await _get_all(db, stmt, Deal, lambda q: q.filter(Deal.organisation_id == organisation_id))

    total_outstanding = Decimal("0.00")
    bucket_0_30 = Decimal("0.00")
    bucket_31_60 = Decimal("0.00")
    bucket_61_90 = Decimal("0.00")
    bucket_91_120 = Decimal("0.00")
    bucket_120_plus = Decimal("0.00")
    at_risk_items: List[SBPExposureDealItem] = []

    now = datetime.now(timezone.utc)

    for deal in deals:
        # Check latest quote for total order value
        q_stmt = select(DealQuote).where(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        quote = await _get_first(
            db, q_stmt, DealQuote, lambda q: q.filter(DealQuote.deal_id == deal.id).order_by(desc(DealQuote.created_at))
        )
        invoice_total = Decimal(str(quote.total_quote_price or "0.00")) if quote else Decimal("0.00")
        if invoice_total <= 0:
            continue

        p_stmt = select(PaymentTransaction).where(PaymentTransaction.deal_id == deal.id)
        payments = await _get_all(db, p_stmt, PaymentTransaction, lambda q: q.filter(PaymentTransaction.deal_id == deal.id))
        total_paid = sum((Decimal(str(p.amount)) for p in payments), start=Decimal("0.00"))
        balance = invoice_total - total_paid

        if balance <= 0:
            continue  # Fully settled

        total_outstanding += balance

        # Determine departure date from shipment or deal creation
        s_stmt = select(Shipment).where(Shipment.deal_id == deal.id).order_by(desc(Shipment.created_at))
        shipment = await _get_first(
            db, s_stmt, Shipment, lambda q: q.filter(Shipment.deal_id == deal.id).order_by(desc(Shipment.created_at))
        )
        departure_dt = shipment.atd or shipment.etd if shipment else deal.created_at
        if departure_dt:
            if departure_dt.tzinfo is None:
                departure_dt = departure_dt.replace(tzinfo=timezone.utc)
            days_elapsed = max((now - departure_dt).days, 0)
        else:
            days_elapsed = 0

        days_remaining = 120 - days_elapsed

        # Risk Classification
        if days_remaining < 0:
            risk = "OVERDUE_VIOLATION"
            bucket_120_plus += balance
        elif days_remaining <= 30:
            risk = "CRITICAL_30_DAYS" if days_remaining > 15 else "OVERDUE_CRITICAL"
            bucket_91_120 += balance
        elif days_elapsed > 60:
            risk = "WARNING_60_DAYS"
            bucket_61_90 += balance
        elif days_elapsed > 30:
            risk = "SAFE"
            bucket_31_60 += balance
        else:
            risk = "SAFE"
            bucket_0_30 += balance

        if days_remaining <= 30 or days_remaining < 0:
            at_risk_items.append(
                SBPExposureDealItem(
                    deal_id=deal.id,
                    reference=deal.reference,
                    buyer_name=deal.buyer_name,
                    invoice_total_usd=invoice_total.quantize(Decimal("0.01")),
                    paid_amount_usd=total_paid.quantize(Decimal("0.01")),
                    outstanding_balance_usd=balance.quantize(Decimal("0.01")),
                    days_since_dispatch=days_elapsed,
                    days_remaining_sbp=days_remaining,
                    risk_level=risk,
                )
            )

    return SBPRealizationExposureReport(
        total_outstanding_usd=total_outstanding.quantize(Decimal("0.01")),
        current_bucket_usd=bucket_0_30.quantize(Decimal("0.01")),
        aging_31_60_usd=bucket_31_60.quantize(Decimal("0.01")),
        aging_61_90_usd=bucket_61_90.quantize(Decimal("0.01")),
        aging_91_120_sbp_warning_usd=bucket_91_120.quantize(Decimal("0.01")),
        overdue_120_plus_violation_usd=bucket_120_plus.quantize(Decimal("0.01")),
        at_risk_deals_count=len(at_risk_items),
        at_risk_deals=sorted(at_risk_items, key=lambda x: x.days_remaining_sbp),
    )


async def get_full_executive_analytics(organisation_id: UUID, db: Any) -> ExecutiveAnalyticsResponse:
    """Unified aggregator for instantaneous executive dashboard loading."""
    kpis = await get_executive_kpis(organisation_id, db)
    incoterms = await get_profitability_by_incoterm(organisation_id, db)
    products = await get_profitability_by_product(organisation_id, db)
    markets = await get_destination_markets(organisation_id, db)
    funnel = await get_pipeline_funnel(organisation_id, db)
    sbp = await get_sbp_realization_exposure(organisation_id, db)

    return ExecutiveAnalyticsResponse(
        kpis=kpis,
        profitability_by_incoterm=incoterms,
        profitability_by_product=products,
        destination_markets=markets,
        pipeline_funnel=funnel,
        sbp_exposure=sbp,
        generated_at=datetime.now(timezone.utc),
    )
