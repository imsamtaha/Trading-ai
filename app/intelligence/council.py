from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable


VALID_DECISIONS = {"BUY", "SELL", "HOLD", "EXIT"}


def _bounded_score(value: float, *, field: str) -> float:
    score = float(value)
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(`${field} must be a finite value between 0 and 1`)
    return score


@dataclass(frozen=True)
class AgentOpinion:
    agent: str
    decision: str
    confidence: float
    evidence: tuple[str, ...] = ()
    snapshot_id: str = ""

    def __post_init__(self) -> None:
        agent = self.agent.strip()
        decision = self.decision.upper()
        if not agent:
            raise ValueError("agent must not be empty")
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Unsupported agent decision: {self.decision}")
        confidence = _bounded_score(self.confidence, field="confidence")
        object.__setattr__(self, "agent", agent)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "confidence", confidence)


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
        symbol = symbol.strip().upper()
        snapshot_id = snapshot_id.strip()
        if not symbol:
            raise ValueError("symbol must not be empty")
        if not snapshot_id:
            raise ValueError("snapshot_id must not be empty")

        items = list(opinions)
        if not items:
            raise ValueError("ATLAS Council requires at least one specialist opinion.")
        data_quality = _bounded_score(data_quality, field="data_quality")
        if any(item.snapshot_id and item.snapshot_id != snapshot_id for item in items):
            raise ValueError("All agent opinions must use the current snapshot_id.")

        risk = dict(senior_risk or {})
        risk["assessment"] = str(risk.get("assessment", "UNKNOWN")).upper()

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
            "senior_risk_management": risk,
            "agreement_score": round(agreement, 4),
            "conflict_score": round(conflict, 4),
            "data_quality": round(data_quality, 4),
        }
