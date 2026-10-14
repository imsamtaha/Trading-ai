from __future__ import annotations

from math import isfinite
from typing import Any
from uuid import uuid4
from app.intelligence.council import NON_VOTING_ROLES


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
        specialist_protocol = "specialist_schema_version" in council or "risk_executive" in council
        risk_executive_veto = False
        if specialist_protocol:
            from app.intelligence.specialists import verdict_allows
            risk_executive_veto = (council.get("specialist_schema_version") != 1 or not verdict_allows(
                council.get("risk_executive"), symbol=council.get("symbol"), snapshot_id=council.get("snapshot_id")))

        data_quality = _score_or_none(council.get("data_quality"))
        conflict = _score_or_none(council.get("conflict_score"))
        malformed = data_quality is None or conflict is None
        recovery = council.get("recovery_guardian")
        recovery_veto = False
        if recovery is not None:
            if (not isinstance(recovery, dict) or recovery.get("environment") != "PAPER"
                    or recovery.get("broker_execution_allowed") is not False
                    or recovery.get("authority") != "VETO_ONLY"
                    or type(recovery.get("allowed")) is not bool):
                malformed = True
            else:
                recovery_veto = not recovery["allowed"]

        weights = {"BUY": 0.0, "SELL": 0.0}
        for opinion in opinions:
            if not isinstance(opinion, dict):
                malformed = True
                continue
            if opinion.get("agent") in NON_VOTING_ROLES:
                continue
            decision = str(opinion.get("decision", "")).upper()
            if decision not in weights:
                continue

            raw_confidence = _score_or_none(opinion.get("confidence"))
            calibrated_confidence = _score_or_none(
                opinion.get("calibrated_confidence", opinion.get("confidence"))
            )
            if raw_confidence is None or calibrated_confidence is None:
                malformed = True
                continue
            weights[decision] += calibrated_confidence

        if not opinions:
            decision = "HOLD"
        elif malformed:
            decision = "HOLD"
        elif risk_state != "RISK_ACCEPTABLE":
            decision = "HOLD"
        elif risk_executive_veto:
            decision = "HOLD"
        elif recovery_veto:
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

        result = {
            "decision_id": str(uuid4()),
            "snapshot_id": council.get("snapshot_id"),
            "symbol": council.get("symbol"),
            "decision": decision,
            "confidence": round(confidence, 4),
            "execution_environment": "PAPER",
            "broker_execution_allowed": False,
            "training_profile_version": council.get("training_profile_version"),
            "calibration_active": bool(council.get("calibration_active", False)),
            "reason_codes": self._reason_codes(
                decision=decision,
                risk_state=risk_state,
                conflict=conflict,
                data_quality=data_quality,
                malformed=malformed,
                has_opinions=bool(opinions),
                recovery_veto=recovery_veto,
            ),
        }
        if specialist_protocol:
            result["specialist_schema_version"] = 1
            result["risk_executive"] = council.get("risk_executive")
            if risk_executive_veto:
                result["reason_codes"] = [code for code in result["reason_codes"] if code != "NO_DIRECTIONAL_EDGE"]
                result["reason_codes"].append("RISK_EXECUTIVE_VETO")
                result["confidence"] = 0.0
        return result

    @staticmethod
    def _reason_codes(
        *,
        decision: str,
        risk_state: str,
        conflict: float | None,
        data_quality: float | None,
        malformed: bool,
        has_opinions: bool,
        recovery_veto: bool = False,
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
        if recovery_veto:
            reasons.append("RECOVERY_GUARDIAN_VETO")
        if not reasons:
            reasons.append("COUNCIL_DIRECTION_CONFIRMED" if decision != "HOLD" else "NO_DIRECTIONAL_EDGE")
        return reasons
