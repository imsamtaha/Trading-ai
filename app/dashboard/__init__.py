from fastapi import APIRouter

from app.dashboard.api import router as api_router
from app.dashboard.views import router as views_router

router = APIRouter()
router.include_router(views_router)
router.include_router(api_router)

__all__ = ["router"]
