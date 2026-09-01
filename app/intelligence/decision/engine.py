from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DecisionInput:
    """Evidence supplied to the deterministic ATLAS decision engine."""

    technical_score: float
    macro_score: float
    news_score: float
    geopolitical_score: float
    cross_asset_score: float
    reaction_score: float
    regime: str
    conflict_score: float
    volatility_score: float
    event_risk_score: float


class UnifiedDecisionEngine:
    """ATLAS v2 deterministic decision matrix.

    Directional evidence is normalized to [-1, 1]. Risk inputs are normalized
    to [0, 1]. The engine never submits orders.
    """

    CONTEXT_WEIGHTS = {
        "macro": 0.35,
        "news": 0.20,
        "geopolitical": 0.20,
        "cross_asset": 0.25,
    }

    ACTION_THRESHOLDS = {
        "buy_score": 70.0,
        "sell_score": 30.0,
        "legacy_buy_directional": 0.40,
        "legacy_sell_directional": -0.40,
        "min_confidence": 55.0,
        "max_conflict": 0.45,
        "max_event_risk": 0.80,
    }

    def clamp(self, value: float, low: float = -1.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))

    def unit(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def regime_score(self, regime: str) -> float:
        return {
            "BULL_TREND": 0.70,
            "BEAR_TREND": -0.70,
            "RISK_ON": 0.40,
            "RISK_OFF": -0.40,
            "SIDEWAYS": 0.00,
            "RANGE": 0.00,
            "TRANSITION": 0.00,
            "HIGH_VOLATILITY": 0.00,
            "LOW_VOLATILITY": 0.00,
            "EVENT_DRIVEN": 0.00,
        }.get(str(regime).upper(), 0.00)

    def calculate_context_score(self, data: DecisionInput) -> float:
        values = {
            "macro": self.clamp(data.macro_score),
            "news": self.clamp(data.news_score),
            "geopolitical": self.clamp(data.geopolitical_score),
            "cross_asset": self.clamp(data.cross_asset_score),
        }
        return self.clamp(
            sum(values[name] * weight for name, weight in self.CONTEXT_WEIGHTS.items())
        )

    def calculate_risk_context(self, data: DecisionInput) -> float:
        return self.clamp((data.macro_score + data.cross_asset_score) / 2.0)

    def calculate_directional_score(self, data: DecisionInput) -> float:
        technical = self.clamp(data.technical_score)
        context = self.calculate_context_score(data)
        reaction = self.clamp(data.reaction_score)
        regime = self.regime_score(data.regime)

        score = (
            technical * 0.55
            + context * 0.20
            + reaction * 0.10
            + regime * 0.15
        )
        return self.clamp(score)

    def calculate_conflict_penalty(self, conflict_score: float) -> float:
        return self.unit(conflict_score) * 0.35

    def calculate_event_penalty(self, event_risk_score: float) -> float:
        return self.unit(event_risk_score) * 0.25

    def calculate_volatility_penalty(self, volatility_score: float) -> float:
        return self.unit(volatility_score) * 0.20

    def calculate_confidence(
        self,
        directional_score: float,
        conflict_score: float,
        event_risk_score: float,
        volatility_score: float,
    ) -> float:
        confidence = abs(directional_score) * 100.0
        confidence -= self.calculate_conflict_penalty(conflict_score) * 100.0
        confidence -= self.calculate_event_penalty(event_risk_score) * 100.0
        confidence -= self.calculate_volatility_penalty(volatility_score) * 100.0
        return round(max(0.0, min(100.0, confidence)), 2)

    def risk_level(
        self,
        conflict_score: float,
        event_risk_score: float,
        volatility_score: float,
    ) -> str:
        risk = (
            self.unit(conflict_score) * 0.40
            + self.unit(event_risk_score) * 0.35
            + self.unit(volatility_score) * 0.25
        )
        if risk >= 0.70:
            return "EXTREME"
        if risk >= 0.50:
            return "HIGH"
        if risk >= 0.30:
            return "MEDIUM"
        return "LOW"

    def determine_action(
        self,
        score_100: float,
        confidence: float,
        conflict_score: float,
        event_risk_score: float,
        risk_level: str = "LOW",
    ) -> str:
        """Return BUY/SELL/WAIT while preserving the legacy helper contract.

        New callers pass the 0-100 score produced by ``analyze``. Existing
        callers/tests may pass the historical directional score in [-1, 1].
        ``risk_level`` remains optional for backward compatibility.
        """
        if risk_level == "EXTREME":
            return "NO_TRADE"
        if conflict_score >= self.ACTION_THRESHOLDS["max_conflict"]:
            return "WAIT"
        if event_risk_score >= self.ACTION_THRESHOLDS["max_event_risk"]:
            return "WAIT"
        if confidence < self.ACTION_THRESHOLDS["min_confidence"]:
            return "WAIT"

        # Backward-compatible path for the previous [-1, 1] API.
        if -1.0 <= float(score_100) <= 1.0:
            if score_100 >= self.ACTION_THRESHOLDS["legacy_buy_directional"]:
                return "BUY"
            if score_100 <= self.ACTION_THRESHOLDS["legacy_sell_directional"]:
                return "SELL"
            return "WAIT"

        if score_100 >= self.ACTION_THRESHOLDS["buy_score"]:
            return "BUY"
        if score_100 <= self.ACTION_THRESHOLDS["sell_score"]:
            return "SELL"
        return "WAIT"

    def analyze(self, data: DecisionInput) -> dict[str, Any]:
        directional_score = self.calculate_directional_score(data)
        score_100 = round((directional_score + 1.0) * 50.0, 2)
        confidence = self.calculate_confidence(
            directional_score,
            data.conflict_score,
            data.event_risk_score,
            data.volatility_score,
        )
        risk_level = self.risk_level(
            data.conflict_score,
            data.event_risk_score,
            data.volatility_score,
        )
        action = self.determine_action(
            score_100,
            confidence,
            data.conflict_score,
            data.event_risk_score,
            risk_level,
        )

        bias = "BULLISH" if directional_score > 0.05 else "BEARISH" if directional_score < -0.05 else "NEUTRAL"

        return {
            "decision": action,
            "bias": bias,
            "directional_score": round(directional_score, 4),
            "score": score_100,
            "confidence": confidence,
            "risk_level": risk_level,
            "regime": str(data.regime).upper(),
            "conflict_score": round(self.unit(data.conflict_score), 4),
            "event_risk_score": round(self.unit(data.event_risk_score), 4),
            "volatility_score": round(self.unit(data.volatility_score), 4),
        }
