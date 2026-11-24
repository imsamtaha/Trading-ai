from __future__ import annotations

import os
from typing import Any
from fastapi import APIRouter, HTTPException, Request

from app.auth.supabase_auth import require_user
from app.mt5_demo.routes import _service as mt5_service
from app.users.routes import _repository as user_repository
from .models import CouncilDecision
from .service import ExecutionGuardService

router = APIRouter(prefix="/api/execution-guard", tags=["execution-guard"])
service: ExecutionGuardService | None = None


def _service() -> ExecutionGuardService:
    global service
    if service is None:
        service = ExecutionGuardService(user_repository(), mt5_service())
    return service


def _require_trade_origin(request: Request) -> None:
    if request.cookies.get("atlas_session") and not request.headers.get("authorization"):
        expected = os.getenv("ATLAS_PUBLIC_ORIGIN", "https://justai-atlas.online").rstrip("/")
        if request.headers.get("origin") != expected:
            raise HTTPException(status_code=403, detail="Invalid execution request origin.")


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _service().status(user.user_id)


@router.get("/events")
def events(request: Request) -> list[dict[str, Any]]:
    user = require_user(request)
    return _service().events(user.user_id)


@router.post("/evaluate")
def evaluate(payload: CouncilDecision, request: Request) -> dict[str, Any]:
    user = require_user(request)
    _require_trade_origin(request)
    return _service().evaluate(user.user_id, payload).model_dump(mode="json")


@router.post("/confirm/{draft_id}")
def confirm(draft_id: str, request: Request) -> dict[str, Any]:
    user = require_user(request)
    _require_trade_origin(request)
    try:
        return _service().confirm(user.user_id, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
