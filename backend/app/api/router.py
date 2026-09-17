"""
ExportOS — Central API Router

Aggregates all sub-routers into a single router mounted at /api in main.py.
Add new routers here as phases are implemented.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.organisation import router as organisation_router

api_router = APIRouter()

# ── Phase 0 (Health & Core) ──────────────────────────────────
api_router.include_router(health_router)

# ── Phase 1 (Auth & Organisation) ────────────────────────────
api_router.include_router(auth_router)
api_router.include_router(organisation_router)

# ── Phase 2 (Products) ───────────────────────────────────────
# api_router.include_router(products_router, prefix="/products")

# ── Phase 3 (Inventory) ──────────────────────────────────────
# api_router.include_router(inventory_router, prefix="/inventory")

# ── Phase 4 (Deals) ──────────────────────────────────────────
# api_router.include_router(deals_router, prefix="/deals")
