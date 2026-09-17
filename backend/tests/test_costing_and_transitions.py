"""
ExportOS — Unit Tests for Incoterm Costing, Margin Math & State Machine Graph

Tests strictly deterministic financial calculations and legal state transitions.
"""

from decimal import Decimal
import pytest

from app.models.costing import (
    CostComponent,
    CostComponentType,
    DealQuote,
    Incoterm,
    QuoteStatus,
)
from app.models.deal import Deal, DealLineItem, DealState
from app.services.costing import INCOTERM_COST_MAP, round_curr
from app.services.deal_state import ALLOWED_TRANSITIONS


def test_incoterm_cost_component_mapping():
    """Verify standard Incoterms 2020 cost allocation rules."""
    # EXW must only include Product Base + Packaging
    assert INCOTERM_COST_MAP[Incoterm.EXW] == {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
    }

    # FOB must include Inland Freight, Export Clearance and Port Handling
    assert CostComponentType.INLAND_FREIGHT in INCOTERM_COST_MAP[Incoterm.FOB]
    assert CostComponentType.EXPORT_CLEARANCE in INCOTERM_COST_MAP[Incoterm.FOB]
    assert CostComponentType.PORT_HANDLING in INCOTERM_COST_MAP[Incoterm.FOB]
    assert CostComponentType.OCEAN_FREIGHT not in INCOTERM_COST_MAP[Incoterm.FOB]

    # CIF must include Ocean/Air Freight + Marine Insurance
    assert CostComponentType.OCEAN_FREIGHT in INCOTERM_COST_MAP[Incoterm.CIF]
    assert CostComponentType.INSURANCE in INCOTERM_COST_MAP[Incoterm.CIF]

    # DDP must include Import Duties
    assert CostComponentType.IMPORT_DUTIES in INCOTERM_COST_MAP[Incoterm.DDP]


def test_deterministic_margin_and_unit_price_calculation():
    """
    Test example from Pakistani Exporter spec:
    5,000 Size-5 Match Footballs CIF Hamburg
    - Base Production: $60,000
    - Packaging: $2,500
    - Inland Freight: $1,200
    - Ocean Freight: $3,500
    - Marine Insurance: $800
    Total Cost = $68,000
    Target Margin = 15% ($10,200)
    Total Quote Price = $78,200
    Unit Price = $15.64 / pc
    """
    base_prod = Decimal("60000.00")
    packaging = Decimal("2500.00")
    inland = Decimal("1200.00")
    ocean = Decimal("3500.00")
    insurance = Decimal("800.00")

    total_cost = base_prod + packaging + inland + ocean + insurance
    assert total_cost == Decimal("68000.00")

    margin_pct = Decimal("15.00")
    margin_amt = round_curr(total_cost * (margin_pct / Decimal("100.00")))
    assert margin_amt == Decimal("10200.00")

    total_quote = total_cost + margin_amt
    assert total_quote == Decimal("78200.00")

    total_qty = Decimal("5000")
    unit_price = round_curr(total_quote / total_qty)
    assert unit_price == Decimal("15.64")


def test_allowed_state_machine_transitions():
    """Verify strict deal state progression rules."""
    # INQUIRY can transition to QUOTED, CONFIRMED, or CANCELLED
    assert DealState.QUOTED in ALLOWED_TRANSITIONS[DealState.INQUIRY]
    assert DealState.CANCELLED in ALLOWED_TRANSITIONS[DealState.INQUIRY]
    assert DealState.SHIPPED not in ALLOWED_TRANSITIONS[DealState.INQUIRY]

    # QUOTED can transition to CONFIRMED or CANCELLED
    assert DealState.CONFIRMED in ALLOWED_TRANSITIONS[DealState.QUOTED]
    assert DealState.PAID not in ALLOWED_TRANSITIONS[DealState.QUOTED]

    # CONFIRMED can transition to IN_PRODUCTION or DOCS_READY
    assert DealState.IN_PRODUCTION in ALLOWED_TRANSITIONS[DealState.CONFIRMED]
    assert DealState.DOCS_READY in ALLOWED_TRANSITIONS[DealState.CONFIRMED]

    # Terminal states have no transitions
    assert len(ALLOWED_TRANSITIONS[DealState.CLOSED]) == 0
    assert len(ALLOWED_TRANSITIONS[DealState.CANCELLED]) == 0
