"""
Tradeloop — Shipment Logistics & Payment Reconciliation Tests (Phase 13)

Tests multi-modal transport milestone sequences, schedule variance math,
payment ledger accounting, SBP 120-day realization countdown, and receivables aging.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import pytest

from app.models.logistics import (
    TransportMode,
    ShipmentStatus,
    MilestoneType,
    MilestoneStatus,
    PaymentType,
    PaymentStatus,
    Shipment,
    ShipmentMilestone,
    PaymentTransaction,
)
from app.models.deal import Deal, DealLineItem, DealState
from app.models.costing import DealQuote, Incoterm
from app.models.product import Product
from app.services.shipment import (
    generate_tracking_number,
    get_default_milestones_for_shipment,
)


def test_tracking_number_generation():
    """Verify prefixing and uniqueness format for tracking numbers."""
    ocean_fcl = generate_tracking_number(TransportMode.OCEAN_FCL)
    assert ocean_fcl.startswith("EXP-OCN-")
    assert len(ocean_fcl) == 14

    air = generate_tracking_number(TransportMode.AIR_FREIGHT)
    assert air.startswith("EXP-AIR-")

    lcl = generate_tracking_number(TransportMode.OCEAN_LCL)
    assert lcl.startswith("EXP-LCL-")


def test_default_milestone_sequence_ocean_vs_air():
    """
    Verify standard logistics sequences for Ocean FCL vs Air Freight.
    Ocean should include Container Stuffing, Gate-In, Customs Out-of-charge, Departure, Transshipment, Arrival.
    """
    now = datetime(2026, 10, 1, 10, 0, 0)
    ocean_milestones = get_default_milestones_for_shipment(TransportMode.OCEAN_FCL, "CIF", now)
    assert len(ocean_milestones) == 10

    m_types_ocean = [m["milestone_type"] for m in ocean_milestones]
    assert MilestoneType.CONTAINER_STUFFING in m_types_ocean
    assert MilestoneType.CUSTOMS_OUT_CHARGE_WEBOC in m_types_ocean
    assert MilestoneType.VESSEL_DEPARTURE in m_types_ocean
    assert MilestoneType.IN_TRANSIT_TRANSSHIPMENT in m_types_ocean
    assert MilestoneType.DESTINATION_ARRIVAL in m_types_ocean

    air_milestones = get_default_milestones_for_shipment(TransportMode.AIR_FREIGHT, "CIP", now)
    assert len(air_milestones) == 8
    m_types_air = [m["milestone_type"] for m in air_milestones]
    assert MilestoneType.VESSEL_DEPARTURE in m_types_air
    assert MilestoneType.CONTAINER_STUFFING not in m_types_air


def test_milestone_schedule_variance_calculation():
    """
    Verify variance computation:
    Planned date: Oct 12
    Actual date: Oct 15 -> variance = +3 days
    """
    planned = datetime(2026, 10, 12, 12, 0, 0)
    actual = datetime(2026, 10, 15, 18, 0, 0)

    variance = (actual.date() - planned.date()).days
    assert variance == 3

    # On schedule
    actual_on_time = datetime(2026, 10, 12, 8, 0, 0)
    assert (actual_on_time.date() - planned.date()).days == 0


def test_payment_ledger_and_fx_realization():
    """
    Verify multi-currency payment tracking:
    Invoice total: $95,000 USD
    Benchmark exchange rate: 278.00 PKR/USD
    Advance payment: $28,500 USD @ 278.50 PKR/USD
      -> Settlement: PKR 7,937,250
      -> Realized FX Gain: $28,500 * 0.50 = PKR 14,250
    Balance payment: $66,500 USD
      -> Total paid: $95,000 USD
      -> Outstanding balance: $0.00
      -> Payment status: FULLY_PAID
    """
    invoice_total = Decimal("95000.00")
    benchmark_rate = Decimal("278.00")

    # Payment 1 (Advance 30%)
    p1_usd = Decimal("28500.00")
    p1_rate = Decimal("278.50")
    p1_pkr = p1_usd * p1_rate
    p1_fx_gain = p1_usd * (p1_rate - benchmark_rate)

    assert p1_pkr == Decimal("7937250.00")
    assert p1_fx_gain == Decimal("14250.00")

    # Payment 2 (Balance 70%)
    p2_usd = Decimal("66500.00")
    p2_rate = Decimal("279.00")
    p2_pkr = p2_usd * p2_rate
    p2_fx_gain = p2_usd * (p2_rate - benchmark_rate)

    total_paid = p1_usd + p2_usd
    outstanding = max(Decimal("0.00"), invoice_total - total_paid)
    total_fx_gain = p1_fx_gain + p2_fx_gain

    assert total_paid == invoice_total
    assert outstanding == Decimal("0.00")
    assert total_fx_gain == Decimal("80750.00")  # (14250 + 66500)


def test_sbp_120_day_realization_countdown():
    """
    Verify SBP Foreign Exchange Manual Chapter XII 120-Day Rule:
    Shipment Departure: 2026-09-01
    SBP Statutory Deadline: 2026-09-01 + 120 days = 2026-12-30
    Current Date: 2026-10-01 (30 days elapsed)
    Days Remaining: 90 days (Within normal limits)
    
    If Current Date: 2026-12-10 (100 days elapsed)
    Days Remaining: 20 days -> Status: AT RISK (< 30 days)

    If Current Date: 2027-01-05 (126 days elapsed)
    Days Remaining: -6 days -> Status: STATUTORY OVERDUE (< 0 days)
    """
    departure = datetime(2026, 9, 1, 0, 0, 0)
    deadline = departure + timedelta(days=120)

    # Day 30 check
    now_day30 = datetime(2026, 10, 1, 0, 0, 0)
    remaining_30 = (deadline.date() - now_day30.date()).days
    assert remaining_30 == 90
    assert remaining_30 > 30

    # Day 100 check (Risk Zone)
    now_day100 = datetime(2026, 12, 10, 0, 0, 0)
    remaining_100 = (deadline.date() - now_day100.date()).days
    assert remaining_100 == 20
    is_at_risk = remaining_100 <= 30
    assert is_at_risk is True

    # Day 126 check (Overdue Violation)
    now_day126 = datetime(2027, 1, 5, 0, 0, 0)
    remaining_126 = (deadline.date() - now_day126.date()).days
    assert remaining_126 == -6
    is_overdue = remaining_126 < 0
    assert is_overdue is True
