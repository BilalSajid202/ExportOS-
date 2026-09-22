"""
Tradeloop — Payment & SBP FX Realization Service (Phase 13)

Implements multi-currency payment ledger, SBP Foreign Exchange Manual Chapter XII
120-day export realization countdown, advance payment (e-Form R) tracking,
realized foreign exchange gain/loss calculation, and receivables aging reports.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logistics import (
    PaymentTransaction,
    PaymentType,
    PaymentStatus,
    Shipment,
    ShipmentStatus,
)
from app.models.deal import Deal, DealState
from app.models.costing import DealQuote
from app.schemas.logistics import (
    PaymentCreate,
    DealPaymentSummary,
    ReceivablesAgingReport,
    ReceivablesAgingDealItem,
)


async def record_payment_transaction(
    db: AsyncSession,
    deal_id: UUID,
    organisation_id: UUID,
    payload: PaymentCreate,
) -> PaymentTransaction:
    deal_stmt = select(Deal).where(Deal.id == deal_id, Deal.organisation_id == organisation_id)
    deal_res = await db.execute(deal_stmt)
    deal = deal_res.scalars().first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    # Get quote/deal total to calculate realized exchange difference
    q_stmt = select(DealQuote).where(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at))
    q_res = await db.execute(q_stmt)
    quote = q_res.scalars().first()
    
    # Standard Pakistani interbank benchmark rate if not specified (e.g. 278.00 PKR/USD)
    benchmark_rate = Decimal("278.00")
    realized_rate = payload.realized_exchange_rate or benchmark_rate
    settlement_pkr = payload.amount * realized_rate

    # FX Gain/Loss calculation: difference between realized rate and benchmark
    fx_gain_loss = payload.amount * (realized_rate - benchmark_rate)

    tx = PaymentTransaction(
        organisation_id=organisation_id,
        deal_id=deal_id,
        payment_type=payload.payment_type,
        amount=payload.amount,
        currency=payload.currency or "USD",
        realized_exchange_rate=realized_rate,
        settlement_amount_pkr=settlement_pkr,
        realized_fx_gain_loss=fx_gain_loss,
        payment_date=payload.payment_date or datetime.now(timezone.utc),
        bank_reference=payload.bank_reference,
        bank_charges=payload.bank_charges or Decimal("0.00"),
        bank_name=payload.bank_name,
        notes=payload.notes,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def get_deal_payment_summary(
    db: AsyncSession,
    deal_id: UUID,
    organisation_id: UUID,
) -> DealPaymentSummary:
    deal_stmt = select(Deal).where(Deal.id == deal_id, Deal.organisation_id == organisation_id)
    deal_res = await db.execute(deal_stmt)
    deal = deal_res.scalars().first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    p_stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.deal_id == deal_id, PaymentTransaction.organisation_id == organisation_id)
        .order_by(PaymentTransaction.payment_date)
    )
    p_res = await db.execute(p_stmt)
    transactions = p_res.scalars().all()

    q_stmt = select(DealQuote).where(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at))
    q_res = await db.execute(q_stmt)
    quote = q_res.scalars().first()

    # Determine total invoice amount
    if quote and quote.total_quote_price:
        invoice_total = Decimal(str(quote.total_quote_price))
        currency = quote.currency or "USD"
    else:
        invoice_total = Decimal("0.00")
        currency = "USD"
        for item in deal.line_items or []:
            price = getattr(item, "target_price", None) or (item.product.base_price if item.product else Decimal("10.00"))
            invoice_total += Decimal(str(price or "10.00")) * Decimal(str(item.quantity or 1))

    total_paid = sum((Decimal(str(tx.amount)) for tx in transactions), start=Decimal("0.00"))
    advance_paid = sum((Decimal(str(tx.amount)) for tx in transactions if tx.payment_type == PaymentType.ADVANCE), start=Decimal("0.00"))
    total_fx_gain_loss = sum((Decimal(str(tx.realized_fx_gain_loss or "0.00")) for tx in transactions), start=Decimal("0.00"))

    outstanding = max(Decimal("0.00"), invoice_total - total_paid)

    if total_paid == Decimal("0.00"):
        status = PaymentStatus.UNPAID
    elif total_paid < invoice_total:
        status = PaymentStatus.PARTIALLY_PAID
    elif total_paid == invoice_total:
        status = PaymentStatus.FULLY_PAID
    else:
        status = PaymentStatus.OVERPAID

    # SBP 120-Day Statutory Realization Deadline (FE Manual Chapter XII)
    s_stmt = (
        select(Shipment)
        .where(Shipment.deal_id == deal_id, Shipment.organisation_id == organisation_id)
        .order_by(desc(Shipment.created_at))
    )
    s_res = await db.execute(s_stmt)
    shipment = s_res.scalars().first()

    now = datetime.now(timezone.utc)
    shipment_departure = None
    if shipment:
        shipment_departure = shipment.atd or shipment.etd
    if not shipment_departure:
        shipment_departure = deal.created_at

    if shipment_departure and shipment_departure.tzinfo is None:
        shipment_departure = shipment_departure.replace(tzinfo=timezone.utc)

    sbp_deadline = shipment_departure + timedelta(days=120) if shipment_departure else None
    days_remaining = (sbp_deadline.date() - now.date()).days if sbp_deadline else 120
    is_at_risk = days_remaining <= 30 and outstanding > Decimal("0.00")
    is_overdue = days_remaining < 0 and outstanding > Decimal("0.00")

    return DealPaymentSummary(
        deal_id=deal.id,
        buyer_name=deal.buyer_name,
        invoice_currency=currency,
        total_invoice_amount=invoice_total,
        total_paid_amount=total_paid,
        outstanding_balance=outstanding,
        payment_status=status,
        realized_fx_gain_loss_total=total_fx_gain_loss,
        advance_amount_received=advance_paid,
        sbp_realization_deadline=sbp_deadline,
        sbp_days_remaining=days_remaining,
        is_sbp_at_risk=is_at_risk,
        is_sbp_overdue=is_overdue,
        transactions=transactions,
    )


async def get_receivables_aging_report(
    db: AsyncSession,
    organisation_id: UUID,
) -> ReceivablesAgingReport:
    stmt = (
        select(Deal)
        .where(Deal.organisation_id == organisation_id)
        .order_by(desc(Deal.created_at))
    )
    res = await db.execute(stmt)
    deals = res.scalars().all()

    now = datetime.now(timezone.utc)
    total_receivables = Decimal("0.00")
    current_not_due = Decimal("0.00")
    days_1_30 = Decimal("0.00")
    days_31_60 = Decimal("0.00")
    days_61_90 = Decimal("0.00")
    days_91_120_sbp = Decimal("0.00")
    overdue_120_plus = Decimal("0.00")

    deal_items: List[ReceivablesAgingDealItem] = []

    for d in deals:
        summary = await get_deal_payment_summary(db, d.id, organisation_id)
        if summary.outstanding_balance <= Decimal("0.00"):
            continue

        total_receivables += summary.outstanding_balance

        # Find departure date
        s_stmt = select(Shipment).where(Shipment.deal_id == d.id).order_by(desc(Shipment.created_at))
        s_res = await db.execute(s_stmt)
        shipment = s_res.scalars().first()
        dept_date = (shipment.atd or shipment.etd) if shipment else d.created_at
        if dept_date and dept_date.tzinfo is None:
            dept_date = dept_date.replace(tzinfo=timezone.utc)
        days_since_shipment = (now.date() - dept_date.date()).days if dept_date else 0

        # Categorize into aging bucket
        if days_since_shipment <= 0:
            bucket = "CURRENT"
            current_not_due += summary.outstanding_balance
        elif days_since_shipment <= 30:
            bucket = "1_30"
            days_1_30 += summary.outstanding_balance
        elif days_since_shipment <= 60:
            bucket = "31_60"
            days_31_60 += summary.outstanding_balance
        elif days_since_shipment <= 90:
            bucket = "61_90"
            days_61_90 += summary.outstanding_balance
        elif days_since_shipment <= 120:
            bucket = "91_120_SBP_ALERT"
            days_91_120_sbp += summary.outstanding_balance
        else:
            bucket = "OVERDUE_120_PLUS"
            overdue_120_plus += summary.outstanding_balance

        deal_items.append(
            ReceivablesAgingDealItem(
                deal_id=d.id,
                reference=d.reference,
                buyer_name=d.buyer_name,
                total_invoice=summary.total_invoice_amount,
                paid_amount=summary.total_paid_amount,
                outstanding_balance=summary.outstanding_balance,
                currency=summary.invoice_currency,
                payment_status=summary.payment_status,
                days_since_shipment=days_since_shipment,
                sbp_days_remaining=summary.sbp_days_remaining,
                aging_bucket=bucket,
            )
        )

    return ReceivablesAgingReport(
        total_receivables_usd=total_receivables,
        current_not_due=current_not_due,
        days_1_30=days_1_30,
        days_31_60=days_31_60,
        days_61_90=days_61_90,
        days_91_120_sbp=days_91_120_sbp,
        overdue_120_plus=overdue_120_plus,
        total_deals_count=len(deal_items),
        deals=deal_items,
    )
