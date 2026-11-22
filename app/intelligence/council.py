from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable, Mapping

from app.intelligence.council_training import agent_weight
from app.intelligence.council_calibration import calibrated_confidence


VALID_DECISIONS = {"BUY", "SELL", "HOLD", "EXIT"}


def _bounded_score(value: float, *, field: str) -> float:
    score = float(value)
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"{field} must be a finite value between 0 and 1")
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
    """Normalizes and calibrates specialist-agent outputs without executing trades."""

    def build_package(
        self,
        *,
        symbol: str,
        snapshot_id: str,
        opinions: Iterable[AgentOpinion],
        senior_risk: dict[str, Any],
        data_quality: float,
        agent_profile: Mapping[str, Any] | None = None,
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
        if len({item.agent for item in items}) != len(items):
            raise ValueError("Duplicate agent identity in council opinions.")
        data_quality = _bounded_score(data_quality, field="data_quality")
        if any(item.snapshot_id and item.snapshot_id != snapshot_id for item in items):
            raise ValueError("All agent opinions must use the current snapshot_id.")

        risk = dict(senior_risk or {})
        risk["assessment"] = str(risk.get("assessment", "UNKNOWN")).upper()

        normalized: list[dict[str, Any]] = []
        for item in items:
            weight = agent_weight(agent_profile, item.agent)
            calibrated = max(0.0, min(1.0, item.confidence * weight))
            if isinstance(agent_profile, Mapping) and agent_profile.get("version") == 2:
                calibrated = calibrated_confidence(agent_profile, item.agent, item.confidence)
            normalized.append(
                {
                    "agent": item.agent,
                    "decision": item.decision,
                    "confidence": item.confidence,
                    "agent_weight": round(weight, 4),
                    "calibrated_confidence": round(calibrated, 4),
                    "evidence": list(item.evidence),
                }
            )

        actionable = [item for item in normalized if item["decision"] in {"BUY", "SELL"}]
        buy_weight = sum(item["calibrated_confidence"] for item in actionable if item["decision"] == "BUY")
        sell_weight = sum(item["calibrated_confidence"] for item in actionable if item["decision"] == "SELL")
        total_weight = buy_weight + sell_weight

        if total_weight:
            agreement = max(buy_weight, sell_weight) / total_weight
            conflict = min(buy_weight, sell_weight) / total_weight
        else:
            agreement, conflict = 0.0, 0.0

        profile_version = agent_profile.get("version") if isinstance(agent_profile, Mapping) else None
        return {
            "symbol": symbol,
            "snapshot_id": snapshot_id,
            "opinions": normalized,
            "senior_risk_management": risk,
            "agreement_score": round(agreement, 4),
            "conflict_score": round(conflict, 4),
            "data_quality": round(data_quality, 4),
            "calibration_active": bool(agent_profile),
            "training_profile_version": profile_version,
        }
