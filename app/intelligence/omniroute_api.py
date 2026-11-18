"""Owner-authenticated, read-only OmniRoute research surface.

No Council weights, broker order functions, or provider management actions here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.owner_dashboard import owner_only
from app.intelligence.omniroute_gateway import OmniRouteResearchGateway


router = APIRouter(prefix="/sam/api/omniroute", tags=["atlas-owner-omniroute"])


class MarketResearchPayload(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    timeframe: str = Field(min_length=1, max_length=12)
    observations: list[str] = Field(min_length=1, max_length=10)


@router.get("/status", include_in_schema=False)
def gateway_status(_: None = Depends(owner_only)) -> dict:
    return OmniRouteResearchGateway().status()


@router.post("/research", include_in_schema=False)
def gateway_research(payload: MarketResearchPayload, _: None = Depends(owner_only)) -> dict:
    try:
        return OmniRouteResearchGateway().research(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            observations=payload.observations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
