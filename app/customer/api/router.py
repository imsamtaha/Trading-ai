from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.customer.auth import CustomerAuthError, verify_supabase_access_token
from app.customer.service import CustomerAccessError, customer_service


router = APIRouter()


class DemoCyclePayload(BaseModel):
    symbol: str = Field(default="EURUSD", min_length=1, max_length=40)
    timeframe: str = Field(default="5m", pattern="^(5m|15m|30m|1h)$")
    demo_volume: float = Field(default=0.1, gt=0)
    requested_risk_pct: float = Field(default=1.0, gt=0, le=2.0)


def _subject(authorization: str | None = Header(default=None)) -> str:
    try:
        return verify_supabase_access_token(authorization)
    except CustomerAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _identity(
    x_customer_id: str = Header(...),
    x_account_id: str = Header(...),
    authorization: str | None = Header(default=None),
) -> tuple[str, str]:
    try:
        subject = verify_supabase_access_token(authorization)
    except CustomerAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        customer_service.authorize(x_customer_id, x_account_id, auth_subject=subject)
    except CustomerAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return x_customer_id, x_account_id


@router.get("/api/v2/customer/accounts")
def accounts(subject: str = Depends(_subject)):
    return {"accounts": customer_service.accounts_for_subject(subject)}


@router.get("/api/v2/customer/account")
def account(identity: tuple[str, str] = Depends(_identity)):
    return customer_service.account(*identity)


@router.get("/api/v2/customer/positions")
def positions(identity: tuple[str, str] = Depends(_identity)):
    customer_id, account_id = identity
    return {"customer_id": customer_id, "account_id": account_id, "positions": customer_service.list_positions(customer_id, account_id)}


@router.get("/api/v2/customer/decisions/latest")
def latest_decision(identity: tuple[str, str] = Depends(_identity)):
    return customer_service.latest_decision(*identity)


@router.get("/api/v2/customer/agents/status")
def agents_status(identity: tuple[str, str] = Depends(_identity)):
    customer_id, account_id = identity
    return {"customer_id": customer_id, "account_id": account_id, **customer_service.agent_status[(customer_id, account_id)]}


@router.get("/api/v2/customer/alerts")
def alerts(identity: tuple[str, str] = Depends(_identity)):
    customer_id, account_id = identity
    return {"customer_id": customer_id, "account_id": account_id, "alerts": customer_service.list_alerts(customer_id, account_id)}


@router.get("/api/v2/customer/rescue/status")
def rescue_status(identity: tuple[str, str] = Depends(_identity)):
    customer_id, account_id = identity
    return {"customer_id": customer_id, "account_id": account_id, **customer_service.rescue[(customer_id, account_id)]}


@router.post("/api/v2/customer/cycle/demo")
def cycle_demo(payload: DemoCyclePayload = Body(default=DemoCyclePayload()), identity: tuple[str, str] = Depends(_identity)):
    try:
        return customer_service.start_demo_cycle(*identity, **payload.model_dump())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/v2/internal/replay")
def replay(payload: dict, identity: tuple[str, str] = Depends(_identity)):
    return {"customer_id": identity[0], "account_id": identity[1], "status": "ACCEPTED", "snapshot_ids": list(payload.get("snapshot_ids", []))}


@router.get("/api/v2/internal/audit/{trace_id}")
def audit_trace(trace_id: str, identity: tuple[str, str] = Depends(_identity)):
    try:
        return {"trace_id": trace_id, "events": customer_service.audit_trace(identity[0], identity[1], trace_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
