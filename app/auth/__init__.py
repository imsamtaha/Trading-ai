from fastapi import APIRouter

from .routes import router as auth_routes
from app.users.routes import router as users_router
from app.mt5_demo.routes import router as mt5_demo_router

router = APIRouter()
router.include_router(auth_routes)
router.include_router(users_router)
router.include_router(mt5_demo_router)

__all__ = ["router"]
