from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.supabase_auth import require_user
from app.billing.entitlements import paid_access
from app.mt5_demo.service import MT5DemoError, MT5DemoService
from app.users.routes import _repository as user_repository, _is_owner

router = APIRouter(prefix="/api/mt5-demo", tags=["mt5-demo"])
service: MT5DemoService | None = None


class ManualOrderPayload(BaseModel):
    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    account_type: Literal["DEMO", "REAL"]
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    direction: Literal["BUY", "SELL"]
    volume: float = Field(gt=0, le=1, allow_inf_nan=False)
    stop_loss: float = Field(gt=0, allow_inf_nan=False)
    take_profit: float = Field(gt=0, allow_inf_nan=False)
    confirmed: Literal[True]


class ActivationPayload(BaseModel):
    account_type: Literal["REAL"]
    confirmed: Literal[True]


class DemoConnectPayload(BaseModel):
    login: int
    password: str = Field(min_length=1, max_length=256)
    server: str = Field(min_length=1, max_length=120)
    broker: str = Field(default="FxPro", max_length=80)


def _service() -> MT5DemoService:
    global service
    if service is None:
        service = MT5DemoService(user_repository())
    return service


@router.post("/connect")
def connect_demo(payload: DemoConnectPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    try:
        connected = _service().connect_demo(user.user_id, payload.model_dump())
        if _is_owner(user) and payload.login == 592031391 and connected.get("server") == "FxPro-MT5 Demo":
            from app.runtime_control.service import set_demo_execution_enabled, set_learned_council_enabled
            set_demo_execution_enabled(True)
            set_learned_council_enabled(True)
        return connected
    except MT5DemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/disconnect")
def disconnect_demo(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if _is_owner(user):
        from app.runtime_control.service import set_learned_council_enabled
        set_learned_council_enabled(False)
    return _service().disconnect_demo(user.user_id)


@router.get("/state")
def demo_state(request: Request) -> dict[str, Any]:
    user = require_user(request)
    try:
        connector = _service()
        if _is_owner(user) and connector.session_credentials(user.user_id) is None:
            try:
                connector.attach_current_demo(user.user_id)
                session = connector.session_credentials(user.user_id) or {}
                if int(session.get("login", 0)) != 592031391 or session.get("server") != "FxPro-MT5 Demo":
                    connector.disconnect_demo(user.user_id)
            except MT5DemoError:
                pass
        return connector.get_demo_state(user.user_id)
    except MT5DemoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc



@router.post("/connect-real")
def connect_real_read_only(payload: DemoConnectPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    if not (_is_owner(user) or paid_access(user_repository().get_subscription(user.user_id))):
        raise HTTPException(status_code=403, detail="An active paid ATLAS subscription is required for a real account.")
    try:
        return _service().connect_account(user.user_id, payload.model_dump(), "REAL")
    except MT5DemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

def _require_trade_origin(request: Request) -> None:
    if request.cookies.get("atlas_session") and not request.headers.get("authorization"):
        expected = os.getenv("ATLAS_PUBLIC_ORIGIN", "https://justai-atlas.online").rstrip("/")
        if request.headers.get("origin") != expected:
            raise HTTPException(status_code=403, detail="Invalid trading request origin.")


@router.get("/trading-state")
def trading_state(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _service().manual_trading_state(user.user_id)


@router.post("/activate-trading")
def activate_trading(payload: ActivationPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    _require_trade_origin(request)
    if not (_is_owner(user) or paid_access(user_repository().get_subscription(user.user_id))):
        raise HTTPException(status_code=403, detail="An active paid ATLAS subscription is required for real trading.")
    try:
        return _service().activate_manual_trading(user.user_id, payload.account_type)
    except MT5DemoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/order")
def manual_order(payload: ManualOrderPayload, request: Request) -> dict[str, Any]:
    user = require_user(request)
    _require_trade_origin(request)
    if payload.account_type == "REAL" and not (_is_owner(user) or paid_access(user_repository().get_subscription(user.user_id))):
        raise HTTPException(status_code=403, detail="An active paid ATLAS subscription is required for real trading.")
    try:
        return _service().place_manual_order(user.user_id, payload.model_dump())
    except MT5DemoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
