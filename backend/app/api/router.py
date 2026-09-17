"""
ExportOS — Central API Router

Aggregates all sub-routers into a single router mounted at /api in main.py.
Add new routers here as phases are implemented.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.organisation import router as organisation_router
from app.api.products import router as products_router
from app.api.inventory import router as inventory_router
from app.api.deals import router as deals_router
from app.api.inquiries import router as inquiries_router
from app.api.extraction import router as extraction_router
from app.api.documents import router as documents_router

api_router = APIRouter()

# ── Phase 0 (Health & Core) ──────────────────────────────────
api_router.include_router(health_router)

# ── Phase 1 (Auth, Users & Organisation) ─────────────────────
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(organisation_router)

# ── Phase 2 (Products) ───────────────────────────────────────
api_router.include_router(products_router)

# ── Phase 3 (Inventory) ──────────────────────────────────────
api_router.include_router(inventory_router)

# ── Phase 4, 7, 8, 9 (Deals, Costing & Lifecycle) ───────────
api_router.include_router(deals_router)

# ── Phase 5 (Inquiry Ingestion & Artifacts) ───────────────────
api_router.include_router(inquiries_router)

# ── Phase 6 (AI Extraction & Human Review) ───────────────────
api_router.include_router(extraction_router)

# ── Phase 10 & 11 (Export Documents & Consistency Audit) ─────
api_router.include_router(documents_router)
