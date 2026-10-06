from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


VALID_DECISIONS = {"BUY", "SELL", "HOLD", "EXIT"}


@dataclass(frozen=True)
class AgentOpinion:
    agent: str
    decision: str
    confidence: float
    evidence: tuple[str, ...] = ()
    snapshot_id: str = ""

    def __post_init__(self) -> None:
        decision = self.decision.upper()
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Unsupported agent decision: {self.decision}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "decision", decision)


class AtlasCouncilCoordinator:
    """Normalizes specialist-agent outputs without executing trades."""

    def build_package(
        self,
        *,
        symbol: str,
        snapshot_id: str,
        opinions: Iterable[AgentOpinion],
        senior_risk: dict[str, Any],
        data_quality: float,
    ) -> dict[str, Any]:
        items = list(opinions)
        if not items:
            raise ValueError("ATLAS Council requires at least one specialist opinion.")
        if not 0.0 <= float(data_quality) <= 1.0:
            raise ValueError("data_quality must be between 0 and 1")
        if any(item.snapshot_id and item.snapshot_id != snapshot_id for item in items):
            raise ValueError("All agent opinions must use the current snapshot_id.")

        actionable = [item for item in items if item.decision in {"BUY", "SELL"}]
        buy_weight = sum(item.confidence for item in actionable if item.decision == "BUY")
        sell_weight = sum(item.confidence for item in actionable if item.decision == "SELL")
        total_weight = buy_weight + sell_weight

        if total_weight:
            agreement = max(buy_weight, sell_weight) / total_weight
            conflict = min(buy_weight, sell_weight) / total_weight
        else:
            agreement, conflict = 0.0, 0.0

        return {
            "symbol": symbol,
            "snapshot_id": snapshot_id,
            "opinions": [
                {
                    "agent": item.agent,
                    "decision": item.decision,
                    "confidence": item.confidence,
                    "evidence": list(item.evidence),
                }
                for item in items
            ],
            "senior_risk_management": senior_risk,
            "agreement_score": round(agreement, 4),
            "conflict_score": round(conflict, 4),
            "data_quality": round(float(data_quality), 4),
        }
