from __future__ import annotations

from typing import Any


class SignalQualityEngine:
    """Separates directional strength, evidence quality, and execution confidence."""

    def evaluate(self, decision: dict[str, Any], mtf_alignment: str = "UNKNOWN") -> dict[str, Any]:
        score = float(decision.get("score", 50.0))
        directional_strength = round(abs(score - 50.0) * 2.0, 2)
        conflict = max(0.0, min(1.0, float(decision.get("conflict_score", 0.0))))
        event_risk = max(0.0, min(1.0, float(decision.get("event_risk_score", 0.0))))
        volatility = max(0.0, min(1.0, float(decision.get("volatility_score", 0.0))))

        alignment_bonus = {
            "STRONG": 1.0,
            "ALIGNED": 0.90,
            "MODERATE": 0.75,
            "MIXED": 0.60,
            "WEAK": 0.45,
        }.get(str(mtf_alignment).upper(), 0.50)

        evidence_quality = 100.0 * (
            0.55 * alignment_bonus
            + 0.20 * (1.0 - conflict)
            + 0.15 * (1.0 - event_risk)
            + 0.10 * (1.0 - volatility)
        )

        execution_confidence = directional_strength * (
            0.45 + 0.55 * evidence_quality / 100.0
        )
        execution_confidence *= max(0.0, 1.0 - 0.35 * conflict)
        execution_confidence *= max(0.0, 1.0 - 0.25 * event_risk)
        execution_confidence *= max(0.0, 1.0 - 0.20 * volatility)

        if execution_confidence >= 75:
            quality = "HIGH"
        elif execution_confidence >= 55:
            quality = "MEDIUM"
        elif execution_confidence >= 35:
            quality = "LOW"
        else:
            quality = "VERY_LOW"

        return {
            "directional_strength": round(directional_strength, 2),
            "evidence_quality": round(evidence_quality, 2),
            "execution_confidence": round(execution_confidence, 2),
            "signal_quality": quality,
        }
