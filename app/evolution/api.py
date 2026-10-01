from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.evolution.engine import EvolutionEngine
from app.evolution.models import AgentMetrics


router = APIRouter(prefix="/evolution", tags=["evolution"])
engine = EvolutionEngine()


class MetricsPayload(BaseModel):
    risk_adjusted_return: float = Field(ge=0.0, le=1.0)
    directional_accuracy: float = Field(ge=0.0, le=1.0)
    calibration: float = Field(ge=0.0, le=1.0)
    drawdown_control: float = Field(ge=0.0, le=1.0)
    regime_accuracy: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)

    def to_metrics(self) -> AgentMetrics:
        return AgentMetrics(**self.dict())


class RecordPayload(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    metrics: MetricsPayload


class CandidatePayload(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    incumbent: MetricsPayload
    candidate: MetricsPayload
    candidate_prompt: str = Field(min_length=1, max_length=20000)


@router.get("/status")
def evolution_status():
    return engine.status()


def _require_writes_enabled() -> None:
    if os.getenv("ATLAS_EVOLUTION_WRITES_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Evolution writes are disabled.")


@router.post("/score")
def score_agent(payload: RecordPayload):
    _require_writes_enabled()
    result = engine.record(payload.agent, payload.metrics.to_metrics())
    return {
        "agent": payload.agent,
        **result,
        "normalized_weights": engine.normalized_weights(),
    }


@router.post("/evaluate")
def evaluate_candidate(payload: CandidatePayload):
    _require_writes_enabled()
    decision = engine.evaluate_candidate(
        agent=payload.agent,
        incumbent_metrics=payload.incumbent.to_metrics(),
        candidate_metrics=payload.candidate.to_metrics(),
        candidate_prompt=payload.candidate_prompt,
    )
    return decision.as_dict()
