from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.supabase_auth import require_user
from app.mt5_demo.service import MT5DemoError, MT5DemoService
from app.users.routes import _repository as user_repository

router = APIRouter(prefix="/api/mt5-demo", tags=["mt5-demo"])
service: MT5DemoService | None = None


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
        return _service().connect_demo(user.user_id, payload.model_dump())
    except MT5DemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/disconnect")
def disconnect_demo(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _service().disconnect_demo(user.user_id)


@router.get("/state")
def demo_state(request: Request) -> dict[str, Any]:
    user = require_user(request)
    try:
        return _service().get_demo_state(user.user_id)
    except MT5DemoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
