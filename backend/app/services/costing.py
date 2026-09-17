"""
ExportOS — Incoterm Costing & Quotation Service (Phase 8)

Strictly deterministic fixed-point arithmetic using Python's Decimal.
No LLM arithmetic allowed for costing or quotations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.costing import (
    CostComponent,
    CostComponentType,
    DealQuote,
    Incoterm,
    QuoteStatus,
)
from app.models.deal import Deal, DealLineItem


# Mapping of which cost types are included in each Incoterm
INCOTERM_COST_MAP: Dict[Incoterm, Set[CostComponentType]] = {
    Incoterm.EXW: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
    },
    Incoterm.FCA: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.OTHER,
    },
    Incoterm.FOB: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OTHER,
    },
    Incoterm.CFR: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.OTHER,
    },
    Incoterm.CIF: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.INSURANCE,
        CostComponentType.OTHER,
    },
    Incoterm.CPT: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.OTHER,
    },
    Incoterm.CIP: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.INSURANCE,
        CostComponentType.OTHER,
    },
    Incoterm.DAP: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.INSURANCE,
        CostComponentType.OTHER,
    },
    Incoterm.DDP: {
        CostComponentType.PRODUCT_BASE,
        CostComponentType.PACKAGING,
        CostComponentType.INLAND_FREIGHT,
        CostComponentType.EXPORT_CLEARANCE,
        CostComponentType.PORT_HANDLING,
        CostComponentType.OCEAN_FREIGHT,
        CostComponentType.AIR_FREIGHT,
        CostComponentType.INSURANCE,
        CostComponentType.IMPORT_DUTIES,
        CostComponentType.OTHER,
    },
}


def round_curr(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using standard ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_deal_cost_components(
    db: AsyncSession,
    organisation_id: UUID,
    deal_id: UUID,
) -> List[CostComponent]:
    """Retrieves all cost components recorded for a deal."""
    result = await db.execute(
        select(CostComponent)
        .where(
            CostComponent.organisation_id == organisation_id,
            CostComponent.deal_id == deal_id,
        )
        .order_by(CostComponent.created_at.asc())
    )
    return list(result.scalars().all())


async def calculate_deal_quote(
    db: AsyncSession,
    deal: Deal,
    incoterm: Incoterm,
    incoterm_place: str,
    margin_percentage: Decimal,
    currency: str = "USD",
    notes: Optional[str] = None,
) -> DealQuote:
    """
    Computes quotation strictly with deterministic decimal mathematics.
    Categorizes base product costs vs logistics/regulatory costs per Incoterm rules.
    """
    components = await get_deal_cost_components(db, deal.organisation_id, deal.id)
    included_types = INCOTERM_COST_MAP.get(incoterm, set())

    base_cost = Decimal("0.00")
    logistics_cost = Decimal("0.00")

    # If components exist, sum up according to Incoterm applicability
    for comp in components:
        if comp.cost_type in included_types:
            if comp.cost_type in {CostComponentType.PRODUCT_BASE, CostComponentType.PACKAGING}:
                base_cost += comp.amount
            else:
                logistics_cost += comp.amount

    total_cost = base_cost + logistics_cost
    margin_dec = (margin_percentage / Decimal("100.00"))
    margin_amount = round_curr(total_cost * margin_dec)
    total_quote_price = total_cost + margin_amount

    # Compute total quantity across line items
    total_qty = sum(li.quantity for li in deal.line_items) if deal.line_items else Decimal("1")
    if total_qty <= Decimal("0"):
        total_qty = Decimal("1")

    unit_price = round_curr(total_quote_price / total_qty)

    quote = DealQuote(
        organisation_id=deal.organisation_id,
        deal_id=deal.id,
        incoterm=incoterm,
        incoterm_place=incoterm_place.strip(),
        currency=currency,
        base_cost=round_curr(base_cost),
        logistics_cost=round_curr(logistics_cost),
        total_cost=round_curr(total_cost),
        margin_percentage=margin_percentage,
        margin_amount=margin_amount,
        total_quote_price=round_curr(total_quote_price),
        unit_price=unit_price,
        status=QuoteStatus.DRAFT,
        notes=notes,
    )
    return quote
