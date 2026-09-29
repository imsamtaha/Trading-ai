"""ATLAS billing integration."""

from fastapi import APIRouter
from app.billing.offers import router as offers_router
from app.billing.routes import router as billing_router
from app.billing.whish import router as whish_router

router = APIRouter()
router.include_router(billing_router)
router.include_router(offers_router)
router.include_router(whish_router)

__all__ = ["router"]
