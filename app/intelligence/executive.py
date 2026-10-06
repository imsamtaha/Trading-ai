from __future__ import annotations

from math import isfinite
from typing import Any
from uuid import uuid4


def _score_or_none(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        return None
    return score


class AtlasExecutiveAgent:
    """Final decision layer for ATLAS paper-trading intelligence.

    This component produces a TradeIntent. It has no broker adapter and cannot
    send a live or demo broker order.
    """

    def decide(self, council: dict[str, Any]) -> dict[str, Any]:
        opinions = council.get("opinions") or []

        risk = council.get("senior_risk_management") or {}
        if not isinstance(risk, dict):
            risk = {}
        risk_state = str(risk.get("assessment", "UNKNOWN")).upper()

        data_quality = _score_or_none(council.get("data_quality"))
        conflict = _score_or_none(council.get("conflict_score"))
        malformed = data_quality is None or conflict is None

        weights = {"BUY": 0.0, "SELL": 0.0}
        for opinion in opinions:
            if not isinstance(opinion, dict):
                malformed = True
                continue
            decision = str(opinion.get("decision", "")).upper()
            if decision not in weights:
                continue
            confidence = _score_or_none(opinion.get("confidence"))
            if confidence is None:
                malformed = True
                continue
            weights[decision] += confidence

        if not opinions:
            decision = "HOLD"
        elif malformed:
            decision = "HOLD"
        elif risk_state != "RISK_ACCEPTABLE":
            decision = "HOLD"
        elif data_quality < 0.5:
            decision = "HOLD"
        elif conflict >= 0.45:
            decision = "HOLD"
        elif weights["BUY"] == weights["SELL"]:
            decision = "HOLD"
        else:
            decision = "BUY" if weights["BUY"] > weights["SELL"] else "SELL"

        if malformed or data_quality is None or conflict is None:
            confidence = 0.0
        else:
            total = weights["BUY"] + weights["SELL"]
            confidence = 0.0 if not total else max(weights.values()) / total
            confidence *= max(0.0, 1.0 - conflict)
            confidence *= data_quality

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
                malformed=malformed,
                has_opinions=bool(opinions),
            ),
        }

    @staticmethod
    def _reason_codes(
        *,
        decision: str,
        risk_state: str,
        conflict: float | None,
        data_quality: float | None,
        malformed: bool,
        has_opinions: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not has_opinions:
            reasons.append("NO_COUNCIL_OPINIONS")
        if malformed:
            reasons.append("MALFORMED_COUNCIL")
        if risk_state == "RISK_REJECT":
            reasons.append("SENIOR_RISK_REJECT")
        elif risk_state != "RISK_ACCEPTABLE":
            reasons.append("SENIOR_RISK_NOT_APPROVED")
        if data_quality is not None and data_quality < 0.5:
            reasons.append("LOW_DATA_QUALITY")
        if conflict is not None and conflict >= 0.45:
            reasons.append("HIGH_COUNCIL_CONFLICT")
        if not reasons:
            reasons.append("COUNCIL_DIRECTION_CONFIRMED" if decision != "HOLD" else "NO_DIRECTIONAL_EDGE")
        return reasons
