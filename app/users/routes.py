from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.auth.supabase_auth import require_user
from app.users.repository import MemoryUserRepository, SupabaseUserRepository, UserRepositoryError

router = APIRouter(tags=["users"])
repository: Any | None = None


class SettingsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    language: str | None = None
    theme: str | None = None


def _repository():
    global repository
    if repository is not None:
        return repository
    try:
        repository = SupabaseUserRepository()
        return repository
    except UserRepositoryError as exc:
        raise HTTPException(status_code=503, detail="User persistence unavailable.") from exc


@router.get("/api/me")
def api_me(request: Request) -> dict[str, Any]:
    user = require_user(request)
    repo = _repository()
    profile = repo.get_or_create_profile(user.user_id, email=user.email)
    subscription = repo.get_subscription(user.user_id)
    return {"user": profile, "subscription": subscription}


@router.get("/api/user/settings")
def get_settings(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _repository().get_user_settings(user.user_id)


@router.put("/api/user/settings")
def put_settings(payload: SettingsPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    values = {key: value for key, value in payload.model_dump().items() if value is not None}
    return _repository().update_user_settings(user.user_id, values)


@router.get("/api/user/dashboard")
def user_dashboard(request: Request) -> dict[str, Any]:
    user = require_user(request)
    repo = _repository()
    repo.get_or_create_profile(user.user_id, email=user.email)
    subscription = repo.get_subscription(user.user_id)
    from app.mt5_demo.routes import _service as mt5_service
    return {
        "user": {"user_id": user.user_id, "email": user.email},
        "plan": str(subscription.get("plan", "FREE")).upper(),
        "mt5": mt5_service().get_dashboard_state(user.user_id),
    }
