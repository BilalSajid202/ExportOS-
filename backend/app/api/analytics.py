"""
Tradeloop — Executive Analytics API Endpoints (Phase 15)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.analytics import (
    ExecutiveKPISummary,
    ProfitabilityByIncoterm,
    ProfitabilityByProduct,
    DestinationMarketAnalytics,
    DealStateDistribution,
    SBPRealizationExposureReport,
    ExecutiveAnalyticsResponse,
)
from app.services.analytics import (
    get_executive_kpis,
    get_profitability_by_incoterm,
    get_profitability_by_product,
    get_destination_markets,
    get_pipeline_funnel,
    get_sbp_realization_exposure,
    get_full_executive_analytics,
)

router = APIRouter(prefix="/analytics", tags=["Executive Analytics & Profitability"])


@router.get("/executive-summary", response_model=ExecutiveAnalyticsResponse)
async def get_executive_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified endpoint returning complete executive KPI metrics, profitability breakdowns,
    pipeline funnel distribution, and SBP 120-day realization exposure.
    """
    return await get_full_executive_analytics(current_user.organisation_id, db)


@router.get("/kpis", response_model=ExecutiveKPISummary)
async def get_kpi_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns top-line financial and operational KPI indicators."""
    return await get_executive_kpis(current_user.organisation_id, db)


@router.get("/profitability/incoterms", response_model=List[ProfitabilityByIncoterm])
async def get_incoterm_profitability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns gross profit margins and revenue grouped by Incoterm."""
    return await get_profitability_by_incoterm(current_user.organisation_id, db)


@router.get("/profitability/products", response_model=List[ProfitabilityByProduct])
async def get_product_profitability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns sales volume and profit contribution per Master SKU."""
    return await get_profitability_by_product(current_user.organisation_id, db)


@router.get("/markets", response_model=List[DestinationMarketAnalytics])
async def get_markets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns pipeline distribution across destination countries."""
    return await get_destination_markets(current_user.organisation_id, db)


@router.get("/pipeline", response_model=List[DealStateDistribution])
async def get_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns deal counts and monetary volume per state machine stage."""
    return await get_pipeline_funnel(current_user.organisation_id, db)


@router.get("/sbp-exposure", response_model=SBPRealizationExposureReport)
async def get_sbp_exposure(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns SBP Chapter XII 120-day realization aging and at-risk receivables."""
    return await get_sbp_realization_exposure(current_user.organisation_id, db)
