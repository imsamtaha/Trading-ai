from __future__ import annotations

from typing import Any
from uuid import uuid4


class AtlasExecutiveAgent:
    """Final decision layer for ATLAS paper-trading intelligence.

    This component produces a TradeIntent. It has no broker adapter and cannot
    send a live or demo broker order.
    """

    def decide(self, council: dict[str, Any]) -> dict[str, Any]:
        opinions = council.get("opinions") or []
        if not opinions:
            raise ValueError("Council package has no opinions.")

        risk = council.get("senior_risk_management") or {}
        risk_state = str(risk.get("assessment", "UNKNOWN")).upper()
        data_quality = float(council.get("data_quality", 0.0))
        conflict = float(council.get("conflict_score", 1.0))

        weights = {"BUY": 0.0, "SELL": 0.0}
        for opinion in opinions:
            decision = str(opinion.get("decision", "")).upper()
            if decision in weights:
                weights[decision] += float(opinion.get("confidence", 0.0))

        if data_quality < 0.5 or risk_state == "RISK_REJECT":
            decision = "HOLD"
        elif conflict >= 0.45:
            decision = "HOLD"
        elif weights["BUY"] == weights["SELL"]:
            decision = "HOLD"
        else:
            decision = "BUY" if weights["BUY"] > weights["SELL"] else "SELL"

        total = weights["BUY"] + weights["SELL"]
        confidence = 0.0 if not total else max(weights.values()) / total
        confidence *= max(0.0, 1.0 - conflict)
        confidence *= max(0.0, min(1.0, data_quality))

        return {
            "decision_id": str(uuid4()),
            "snapshot_id": council.get("snapshot_id"),
            "symbol": council.get("symbol"),
            "decision": decision,
            "confidence": round(confidence, 4),
            "execution_environment": "PAPER",
            "broker_execution_allowed": False,
            "reason_codes": self._reason_codes(
                decision=decision,
                risk_state=risk_state,
                conflict=conflict,
                data_quality=data_quality,
            ),
        }

    @staticmethod
    def _reason_codes(*, decision: str, risk_state: str, conflict: float, data_quality: float) -> list[str]:
        reasons: list[str] = []
        if risk_state == "RISK_REJECT":
            reasons.append("SENIOR_RISK_REJECT")
        if data_quality < 0.5:
            reasons.append("LOW_DATA_QUALITY")
        if conflict >= 0.45:
            reasons.append("HIGH_COUNCIL_CONFLICT")
        if not reasons:
            reasons.append("COUNCIL_DIRECTION_CONFIRMED" if decision != "HOLD" else "NO_DIRECTIONAL_EDGE")
        return reasons
