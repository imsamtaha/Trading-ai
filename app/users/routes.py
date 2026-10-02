from __future__ import annotations

from typing import Any
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.users.assistant import AssistantRateLimited, AssistantUnavailable, answer_assistant

from app.auth.supabase_auth import require_user
from app.data.market import get_candles
from app.dashboard.market_briefing import get_market_briefing
from app.billing.plans import access_for_plan
from app.billing.entitlements import paid_access
from app.users.repository import MemoryUserRepository, SupabaseUserRepository, UserRepositoryError

router = APIRouter(tags=["users"])
_CHART_SYMBOLS = {"XAUUSD", "XAGUSD", "GAS", "EURUSD", "XRPUSDT", "SOLUSDT"}
_CHART_INTERVALS = {"5m", "15m", "30m", "1h", "4h", "1d"}
repository: Any | None = None

def _is_owner(user) -> bool:
    configured = os.getenv("ATLAS_OWNER_EMAIL", "").strip().lower()
    return bool(configured and user.email and user.email.strip().lower() == configured)


class AssistantPayload(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


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
    return {"user": {**profile, "role": "OWNER" if _is_owner(user) else "CUSTOMER"}, "subscription": subscription}


@router.get("/api/user/settings")
def get_settings(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _repository().get_user_settings(user.user_id)


@router.put("/api/user/settings")
def put_settings(payload: SettingsPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    values = {key: value for key, value in payload.model_dump().items() if value is not None}
    return _repository().update_user_settings(user.user_id, values)


@router.post("/api/user/assistant")
def user_assistant(payload: AssistantPayload, request: Request) -> dict[str, str]:
    user = require_user(request)
    if not (_is_owner(user) or paid_access(_repository().get_subscription(user.user_id))):
        raise HTTPException(status_code=403, detail="An active ATLAS subscription is required.")
    try:
        return {"message": answer_assistant(user.user_id, payload.message)}
    except AssistantRateLimited as exc:
        raise HTTPException(status_code=429, detail="Assistant rate limit reached.") from exc
    except AssistantUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/market-preview")
def market_preview(symbol: str = "XAUUSD", interval: str = "1h", limit: int = 120) -> dict[str, Any]:
    symbol, interval = symbol.strip().upper(), interval.strip().lower()
    if symbol not in _CHART_SYMBOLS or interval not in _CHART_INTERVALS or not 20 <= limit <= 300:
        raise HTTPException(status_code=400, detail="Unsupported chart parameters.")
    try:
        payload = get_candles(symbol, interval, limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Market data is temporarily unavailable.") from exc
    return {"symbol": symbol, "interval": interval, "count": int(payload.get("count", 0)),
            "candles": payload.get("candles", []), "source": "ATLAS market data"}


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
def user_market_briefing(request: Request, language: str = "en") -> dict[str, Any]:
    user = require_user(request)
    if not (_is_owner(user) or paid_access(_repository().get_subscription(user.user_id))):
        raise HTTPException(status_code=403, detail="An active ATLAS subscription is required.")
    return get_market_briefing(language="ar" if language.lower().startswith("ar") else "en")


@router.get("/api/user/dashboard")
def user_dashboard(request: Request) -> dict[str, Any]:
    user = require_user(request)
    repo = _repository()
    repo.get_or_create_profile(user.user_id, email=user.email)
    subscription = repo.get_subscription(user.user_id)
    owner = _is_owner(user)
    from app.mt5_demo.routes import _service as mt5_service
    from app.mt5_demo.service import MT5DemoError
    from app.execution_guard.routes import _service as execution_guard_service
    mt5 = mt5_service()
    session_getter = getattr(mt5, "session_credentials", None)
    current_attacher = getattr(mt5, "attach_current_demo", None)
    if owner and callable(session_getter) and callable(current_attacher) and session_getter(user.user_id) is None:
        try:
            current_attacher(user.user_id)
        except MT5DemoError:
            pass
    dashboard = mt5.get_dashboard_state(user.user_id)
    session = session_getter(user.user_id) if callable(session_getter) else None
    if owner and session and session.get("login") == 592031391 and session.get("server") == "FxPro-MT5 Demo":
        # History archived on 2026-10-02 at 23:10:28 UTC; open positions stay visible.
        history_start_ticket = 323402062
        dashboard["recent_trades"] = [
            trade for trade in dashboard.get("recent_trades", [])
            if int(trade.get("time", 0) or 0) >= 1790880044
            and int(trade.get("ticket", 0) or 0) >= history_start_ticket
        ]
        dashboard["history_start_ticket"] = history_start_ticket
        dashboard["history_time_offset_seconds"] = 10800
    return {
        "user": {"user_id": user.user_id, "email": user.email, "role": "OWNER" if owner else "CUSTOMER"},
        "plan": "OWNER" if owner else str(subscription.get("plan", "FREE")).upper(),
        "features": {**access_for_plan("elite" if owner else subscription.get("plan", "FREE")),
                     "trading_intelligence": owner or paid_access(subscription),
                     "demo_executive": owner or paid_access(subscription),
                     "execution_guard": owner or paid_access(subscription)},
        "mt5": dashboard,
        "execution_guard": execution_guard_service().status(user.user_id),
    }
