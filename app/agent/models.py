from dataclasses import asdict, dataclass, field
from typing import Any

MULTI_TIMEFRAMES = ("5m", "15m", "30m", "1h")


@dataclass
class AgentRequest:
    symbol: str
    interval: str = "1h"
    limit: int = 100
    account_balance: float = 10000.0
    risk_percent: float = 1.0


@dataclass
class AgentDecision:
    symbol: str
    interval: str
    decision: str
    confidence: float
    status: str
    rationale: list[str] = field(default_factory=list)
    technical: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] = field(default_factory=dict)
    signal: dict[str, Any] = field(default_factory=dict)
    trade: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    selected_skills: list[str] = field(default_factory=list)
    paper_only: bool = True
    timeframe_decisions: dict[str, Any] = field(default_factory=dict)
    candidate_interval: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
