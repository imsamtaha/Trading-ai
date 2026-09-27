from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.auth.supabase_auth import require_user
from app.demo_executive.service import DemoExecutiveAccessError, DemoExecutiveError, DemoExecutiveService
from app.mt5_demo.routes import _service as mt5_service
from app.users.routes import _repository as user_repository

router = APIRouter(prefix="/api/demo-executive", tags=["demo-executive"])
service: DemoExecutiveService | None = None


def _service() -> DemoExecutiveService:
    global service
    if service is None:
        service = DemoExecutiveService(user_repository(), mt5_service())
    return service


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _service().status(user.user_id)


@router.post("/start")
def start(request: Request) -> dict[str, Any]:
    user = require_user(request)
    try:
        return _service().start(user.user_id)
    except DemoExecutiveAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DemoExecutiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/stop")
def stop(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return _service().stop(user.user_id)


@router.get("/events")
def events(request: Request) -> list[dict[str, Any]]:
    user = require_user(request)
    return _service().events(user.user_id)
