from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Mode(str, Enum):
    LIVE_DEMO = "LIVE_DEMO"
    LIVE_EXECUTION = "LIVE_EXECUTION"


class AgentStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class Signal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"
    NEUTRAL = "NEUTRAL"


class Decision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    EXIT = "EXIT"
    REDUCE = "REDUCE"


@dataclass(frozen=True)
class CustomerContext:
    customer_id: str
    account_id: str
    mode: Mode

    def __post_init__(self) -> None:
        if not self.customer_id or not self.account_id:
            raise ValueError("customer_id and account_id are required")


@dataclass(frozen=True)
class MarketSnapshot:
    snapshot_id: str
    customer_id: str
    account_id: str
    mode: Mode
    symbol: str
    timeframe: str
    market_timestamp: datetime
    snapshot_timestamp: datetime
    market: dict[str, Any] = field(default_factory=dict)
    account: dict[str, Any] = field(default_factory=dict)
    system: dict[str, Any] = field(default_factory=dict)
    news: dict[str, Any] | None = None
    sentiment: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentVerdict:
    agent: str
    timestamp: datetime
    snapshot_id: str
    status: AgentStatus
    signal: Signal
    confidence: float
    evidence: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    data_quality: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass(frozen=True)
class DecisionCandidate:
    snapshot_id: str
    customer_id: str
    account_id: str
    mode: Mode
    decision: Decision
    confidence: float
    rationale: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
