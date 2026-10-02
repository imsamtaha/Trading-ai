from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentMetrics:
    risk_adjusted_return: float = 0.0
    directional_accuracy: float = 0.0
    calibration: float = 0.0
    drawdown_control: float = 0.0
    regime_accuracy: float = 0.0
    consistency: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "risk_adjusted_return": float(self.risk_adjusted_return),
            "directional_accuracy": float(self.directional_accuracy),
            "calibration": float(self.calibration),
            "drawdown_control": float(self.drawdown_control),
            "regime_accuracy": float(self.regime_accuracy),
            "consistency": float(self.consistency),
        }


@dataclass(frozen=True)
class EvolutionDecision:
    agent: str
    incumbent_score: float
    candidate_score: float
    action: str
    reason: str
    promoted_prompt: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "incumbent_score": self.incumbent_score,
            "candidate_score": self.candidate_score,
            "action": self.action,
            "reason": self.reason,
            "promoted_prompt": self.promoted_prompt,
        }
