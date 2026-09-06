"""ATLAS billing integrations."""

from fastapi import APIRouter
from app.billing.routes import router as stripe_router
from app.billing.whish import router as whish_router

router = APIRouter()
router.include_router(stripe_router)
router.include_router(whish_router)

__all__ = ["router"]
