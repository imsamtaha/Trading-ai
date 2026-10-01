from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, status as http_status
from pydantic import BaseModel

from app.auth.supabase_auth import require_user
from .service import RuntimeControlError, RuntimeControlService

router = APIRouter(prefix="/api/runtime", tags=["runtime-control"])
service = RuntimeControlService()


class DemoExecutionPayload(BaseModel):
    enabled: bool


def _require_owner(request: Request):
    user = require_user(request)
    configured = os.getenv("ATLAS_OWNER_EMAIL", "").strip().lower()
    if not configured or not user.email or user.email.strip().lower() != configured:
        raise HTTPException(status_code=403, detail="Owner access required.")
    return user


@router.get("/status")
def runtime_status(request: Request) -> dict[str, object]:
    _require_owner(request)
    return service.status()


@router.post("/demo-execution")
def demo_execution(payload: DemoExecutionPayload, request: Request) -> dict[str, object]:
    _require_owner(request)
    return service.set_demo_execution(payload.enabled)


@router.post("/learned-council")
def learned_council(payload: DemoExecutionPayload, request: Request) -> dict[str, object]:
    _require_owner(request)
    if payload.enabled and not service.status()["demo_execution"]:
        raise HTTPException(status_code=409, detail="Enable Demo execution first.")
    return service.set_learned_council(payload.enabled)


@router.post("/restart", status_code=http_status.HTTP_202_ACCEPTED)
def restart_backend(request: Request) -> dict[str, str]:
    _require_owner(request)
    try:
        return service.restart()
    except RuntimeControlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
