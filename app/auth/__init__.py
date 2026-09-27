from fastapi import APIRouter

from .routes import router as auth_routes
from app.users.routes import router as users_router

router = APIRouter()
router.include_router(auth_routes)
router.include_router(users_router)

__all__ = ["router"]
