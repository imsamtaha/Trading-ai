from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.auth.supabase_auth import require_user
from app.data.market import get_candles
from app.dashboard.market_briefing import get_market_briefing
from app.billing.plans import access_for_plan
from app.users.repository import MemoryUserRepository, SupabaseUserRepository, UserRepositoryError

router = APIRouter(tags=["users"])
_CHART_SYMBOLS = {"XAUUSD", "XAGUSD", "GAS", "EURUSD", "XRPUSDT", "SOLUSDT"}
_CHART_INTERVALS = {"5m", "15m", "30m", "1h", "4h", "1d"}
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


@router.get("/api/user/chart-data")
def user_chart_data(request: Request, symbol: str = "XAUUSD", interval: str = "15m", limit: int = 120) -> dict[str, Any]:
    require_user(request)
    symbol, interval = symbol.strip().upper(), interval.strip().lower()
    if symbol not in _CHART_SYMBOLS or interval not in _CHART_INTERVALS or not 20 <= limit <= 300:
        raise HTTPException(status_code=400, detail="Unsupported chart parameters.")
    try:
        payload = get_candles(symbol, interval, limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Chart data is temporarily unavailable.") from exc
    return {"symbol": payload.get("symbol", symbol), "interval": payload.get("interval", interval),
            "count": int(payload.get("count", 0)), "candles": payload.get("candles", []), "source": "ATLAS market data"}


@router.get("/api/user/market-briefing")
def user_market_briefing(request: Request) -> dict[str, Any]:
    require_user(request)
    return get_market_briefing()


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
        "features": access_for_plan(subscription.get("plan", "FREE")),
        "mt5": mt5_service().get_dashboard_state(user.user_id),
    }
