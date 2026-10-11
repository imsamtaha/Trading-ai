from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

DecisionDirection = Literal["BUY", "SELL", "WAIT"]
GuardStatus = Literal["READY", "APPROVED", "BLOCKED", "EXECUTED", "WAITING_CONFIRMATION", "UNKNOWN"]


class CouncilDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    symbol: str = Field(min_length=1, max_length=32)
    direction: DecisionDirection
    confidence: float = Field(ge=0, le=100, allow_inf_nan=False)
    rationale: str = Field(min_length=1, max_length=2000)
    timestamp: datetime
    volume: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    stop_loss: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    take_profit: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    risk_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_trade_fields(self):
        if self.direction != "WAIT" and any(v is None for v in (self.volume, self.stop_loss, self.take_profit)):
            raise ValueError("BUY/SELL decisions require volume, stop_loss, and take_profit")
        return self


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str
    account_type: Literal["DEMO"]
    symbol: str
    direction: Literal["BUY", "SELL"]
    volume: float = Field(gt=0, allow_inf_nan=False)
    stop_loss: float = Field(gt=0, allow_inf_nan=False)
    take_profit: float = Field(gt=0, allow_inf_nan=False)


class GuardResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision_id: str
    status: GuardStatus
    reason: str | None = None
    execution_request: ExecutionRequest | None = None


class TradeDraft(BaseModel):
    model_config = ConfigDict(frozen=True)
    draft_id: str
    user_id: str
    decision_id: str
    account_masked: str
    account_type: Literal["REAL"]
    symbol: str
    direction: Literal["BUY", "SELL"]
    volume: float = Field(gt=0, allow_inf_nan=False)
    stop_loss: float = Field(gt=0, allow_inf_nan=False)
    take_profit: float = Field(gt=0, allow_inf_nan=False)
    confidence: float = Field(ge=0, le=100, allow_inf_nan=False)
    rationale: str
    expires_at: datetime
    status: Literal["WAITING_CONFIRMATION"] = "WAITING_CONFIRMATION"
    council_evidence: dict[str, Any] = Field(default_factory=dict)
    risk_result: dict[str, Any] = Field(default_factory=dict)


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision_id: str
    status: GuardStatus
    created_at: datetime
    reason: str | None = None
    broker_ticket: int | None = None
