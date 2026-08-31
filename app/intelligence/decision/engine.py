from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DecisionInput:
    """Normalized market evidence used by the deterministic ATLAS scorer.

    Each directional component is expected in [-1, 1]. Positive values favor
    LONG/BUY; negative values favor SHORT/SELL.
    """

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
    """Deterministic ATLAS decision matrix.

    The engine converts normalized evidence into a directional score,
    confidence, risk level, and conservative action. It does not submit orders.
    """

    # Weights sum to 1.00. Risk is derived from macro/cross-asset context.
    WEIGHTS = {
        "technical": 0.20,
        "macro": 0.15,
        "news": 0.10,
        "geopolitical": 0.10,
        "cross_asset": 0.15,
        "reaction": 0.10,
        "regime": 0.10,
        "risk": 0.10,
    }

    ACTION_THRESHOLDS = {
        "buy": 0.20,
        "sell": -0.20,
        "min_confidence": 55.0,
        "max_conflict": 0.45,
        "max_event_risk": 0.80,
    }

    HARD_RISK_LIMITS = {
        "extreme_risk": 0.70,
    }

    def clamp(self, value: float, low: float = -1.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))

    def positive_unit(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def regime_score(self, regime: str) -> float:
        mapping = {
            "BULL_TREND": 0.70,
            "BEAR_TREND": -0.70,
            "RISK_ON": 0.40,
            "RISK_OFF": -0.40,
            "SIDEWAYS": 0.00,
            "TRANSITION": 0.00,
            "HIGH_VOLATILITY": 0.00,
            "LOW_VOLATILITY": 0.00,
            "EVENT_DRIVEN": 0.00,
        }
        return mapping.get(str(regime).upper(), 0.00)

    def calculate_risk_context(self, data: DecisionInput) -> float:
        return self.clamp((data.macro_score + data.cross_asset_score) / 2.0)

    def calculate_directional_score(self, data: DecisionInput) -> float:
        values = {
            "technical": self.clamp(data.technical_score),
            "macro": self.clamp(data.macro_score),
            "news": self.clamp(data.news_score),
            "geopolitical": self.clamp(data.geopolitical_score),
            "cross_asset": self.clamp(data.cross_asset_score),
            "reaction": self.clamp(data.reaction_score),
            "regime": self.regime_score(data.regime),
            "risk": self.calculate_risk_context(data),
        }

        score = sum(values[name] * weight for name, weight in self.WEIGHTS.items())
        return self.clamp(score)

    def calculate_conflict_penalty(self, conflict_score: float) -> float:
        return self.positive_unit(conflict_score) * 0.35

    def calculate_event_penalty(self, event_risk_score: float) -> float:
        return self.positive_unit(event_risk_score) * 0.25

    def calculate_volatility_penalty(self, volatility_score: float) -> float:
        return self.positive_unit(volatility_score) * 0.20

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
            self.positive_unit(conflict_score) * 0.40
            + self.positive_unit(event_risk_score) * 0.35
            + self.positive_unit(volatility_score) * 0.25
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
        directional_score: float,
        confidence: float,
        conflict_score: float,
        event_risk_score: float,
        risk_level: str | None = None,
    ) -> str:
        """Apply conservative action gates after scoring."""
        if risk_level == "EXTREME":
            return "NO_TRADE"
        if conflict_score >= self.ACTION_THRESHOLDS["max_conflict"]:
            return "WAIT"
        if event_risk_score >= self.ACTION_THRESHOLDS["max_event_risk"]:
            return "WAIT"
        if confidence < self.ACTION_THRESHOLDS["min_confidence"]:
            return "WAIT"

        if directional_score >= self.ACTION_THRESHOLDS["buy"]:
            return "BUY"
        if directional_score <= self.ACTION_THRESHOLDS["sell"]:
            return "SELL"
        return "WAIT"

    def analyze(self, data: DecisionInput) -> dict:
        directional_score = self.calculate_directional_score(data)
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
            directional_score,
            confidence,
            data.conflict_score,
            data.event_risk_score,
            risk_level,
        )

        if directional_score > 0:
            bias = "BULLISH"
        elif directional_score < 0:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        score_100 = round((directional_score + 1.0) * 50.0, 2)

        return {
            "decision": action,
            "bias": bias,
            "directional_score": round(directional_score, 4),
            "score": score_100,
            "confidence": confidence,
            "risk_level": risk_level,
            "regime": str(data.regime).upper(),
            "conflict_score": round(self.positive_unit(data.conflict_score), 4),
            "event_risk_score": round(self.positive_unit(data.event_risk_score), 4),
            "volatility_score": round(self.positive_unit(data.volatility_score), 4),
        }


if __name__ == "__main__":
    engine = UnifiedDecisionEngine()
    market = DecisionInput(
        technical_score=0.75,
        macro_score=0.30,
        news_score=0.45,
        geopolitical_score=-0.20,
        cross_asset_score=0.40,
        reaction_score=0.60,
        regime="BULL_TREND",
        conflict_score=0.18,
        volatility_score=0.25,
        event_risk_score=0.15,
    )
    print("UNIFIED DECISION ENGINE TEST")
    print("=" * 55)
    for key, value in engine.analyze(market).items():
        print(f"{key}: {value}")
