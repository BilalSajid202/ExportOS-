"""
ExportOS — Executive Analytics & Profitability Schemas (Phase 15)
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ExecutiveKPISummary(BaseModel):
    """Core financial and operational executive metrics."""
    total_pipeline_value_usd: Decimal = Field(default=Decimal("0.00"), description="Total gross value of all active export deals")
    total_realized_revenue_usd: Decimal = Field(default=Decimal("0.00"), description="Total settled export payments in USD")
    total_realized_revenue_pkr: Decimal = Field(default=Decimal("0.00"), description="Total converted inward remittances in PKR")
    average_gross_margin_pct: Decimal = Field(default=Decimal("0.00"), description="Weighted average commercial gross margin % across quotes")
    total_active_deals: int = Field(default=0, description="Count of open/in-progress export deals")
    total_completed_deals: int = Field(default=0, description="Count of reconciled and closed deals")
    sbp_at_risk_exposure_usd: Decimal = Field(default=Decimal("0.00"), description="Receivables approaching or exceeding SBP 120-day realization window")
    doc_consistency_pass_rate_pct: Decimal = Field(default=Decimal("0.00"), description="Audit pass rate of generated cross-document sets")


class ProfitabilityByIncoterm(BaseModel):
    """Gross margin and revenue distribution by Incoterm."""
    incoterm: str
    deal_count: int
    total_revenue_usd: Decimal
    total_cost_usd: Decimal
    total_margin_usd: Decimal
    average_margin_pct: Decimal


class ProfitabilityByProduct(BaseModel):
    """Profit contribution and sales volume per SKU / Master Product."""
    product_id: UUID
    product_name: str
    sku: str
    units_sold: Decimal
    total_revenue_usd: Decimal
    total_cost_usd: Decimal
    gross_margin_pct: Decimal


class DestinationMarketAnalytics(BaseModel):
    """Export market breakdown by destination country."""
    destination_country: str
    deal_count: int
    buyer_count: int
    total_value_usd: Decimal
    percentage_of_pipeline: Decimal


class DealStateDistribution(BaseModel):
    """Pipeline distribution across state machine."""
    state: str
    deal_count: int
    total_value_usd: Decimal


class SBPExposureDealItem(BaseModel):
    """Individual export deal with pending SBP FX realization exposure."""
    deal_id: UUID
    reference: str
    buyer_name: str
    invoice_total_usd: Decimal
    paid_amount_usd: Decimal
    outstanding_balance_usd: Decimal
    days_since_dispatch: int
    days_remaining_sbp: int
    risk_level: str  # "SAFE", "WARNING_30_DAYS", "CRITICAL_15_DAYS", "OVERDUE_VIOLATION"


class SBPRealizationExposureReport(BaseModel):
    """Comprehensive SBP Foreign Exchange Chapter XII receivables aging."""
    total_outstanding_usd: Decimal
    current_bucket_usd: Decimal  # 0-30 days
    aging_31_60_usd: Decimal
    aging_61_90_usd: Decimal
    aging_91_120_sbp_warning_usd: Decimal
    overdue_120_plus_violation_usd: Decimal
    at_risk_deals_count: int
    at_risk_deals: List[SBPExposureDealItem] = []


class ExecutiveAnalyticsResponse(BaseModel):
    """Unified payload for executive dashboard hydration."""
    kpis: ExecutiveKPISummary
    profitability_by_incoterm: List[ProfitabilityByIncoterm] = []
    profitability_by_product: List[ProfitabilityByProduct] = []
    destination_markets: List[DestinationMarketAnalytics] = []
    pipeline_funnel: List[DealStateDistribution] = []
    sbp_exposure: SBPRealizationExposureReport
    generated_at: datetime
