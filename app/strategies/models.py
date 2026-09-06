from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class StrategyCandidate:
    symbol: str
    strategy: str
    direction: str
    regime: str
    confidence: float
    classification: str
    setup_lane: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    qualified: bool
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
