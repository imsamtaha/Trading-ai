from dataclasses import dataclass


@dataclass
class MarketState:
    trend_score: float
    volatility_score: float
    momentum_score: float
    volume_score: float
    event_risk_score: float
    risk_sentiment_score: float


class MarketRegimeEngine:

    def __init__(self):
        self.regimes = {
            "BULL_TREND",
            "BEAR_TREND",
            "RANGE",
            "HIGH_VOLATILITY",
            "LOW_VOLATILITY",
            "RISK_ON",
            "RISK_OFF",
            "EVENT_DRIVEN",
            "TRANSITION",
        }

    def clamp(self, value):
        return max(
            -1.0,
            min(1.0, float(value)),
        )

    def classify_trend(self, score):

        score = self.clamp(score)

        if score >= 0.60:
            return "BULL_TREND"

        if score <= -0.60:
            return "BEAR_TREND"

        return "RANGE"

    def classify_volatility(self, score):

        score = abs(
            self.clamp(score)
        )

        if score >= 0.75:
            return "HIGH_VOLATILITY"

        if score <= 0.25:
            return "LOW_VOLATILITY"

        return "NORMAL_VOLATILITY"

    def classify_risk(self, score):

        score = self.clamp(score)

        if score >= 0.40:
            return "RISK_ON"

        if score <= -0.40:
            return "RISK_OFF"

        return "NEUTRAL_RISK"

    def classify_event_risk(self, score):

        score = max(
            0.0,
            min(1.0, float(score)),
        )

        if score >= 0.75:
            return "EVENT_DRIVEN"

        if score >= 0.40:
            return "ELEVATED_EVENT_RISK"

        return "NORMAL_EVENT_RISK"

    def calculate_regime_score(
        self,
        state,
    ):
        trend = self.clamp(
            state.trend_score
        )

        momentum = self.clamp(
            state.momentum_score
        )

        volume = self.clamp(
            state.volume_score
        )

        risk = self.clamp(
            state.risk_sentiment_score
        )

        return (
            trend * 0.35
            + momentum * 0.25
            + volume * 0.10
            + risk * 0.30
        )

    def detect_primary_regime(
        self,
        state,
    ):
        trend_regime = (
            self.classify_trend(
                state.trend_score
            )
        )

        volatility_regime = (
            self.classify_volatility(
                state.volatility_score
            )
        )

        risk_regime = (
            self.classify_risk(
                state.risk_sentiment_score
            )
        )

        event_regime = (
            self.classify_event_risk(
                state.event_risk_score
            )
        )

        # Major event risk takes priority.
        if event_regime == "EVENT_DRIVEN":
            return "EVENT_DRIVEN"

        # Extreme volatility takes priority.
        if volatility_regime == "HIGH_VOLATILITY":
            return "HIGH_VOLATILITY"

        # Strong directional trend.
        if trend_regime == "BULL_TREND":
            return "BULL_TREND"

        if trend_regime == "BEAR_TREND":
            return "BEAR_TREND"

        # Strong risk environment.
        if risk_regime == "RISK_ON":
            return "RISK_ON"

        if risk_regime == "RISK_OFF":
            return "RISK_OFF"

        return "RANGE"

    def analyze(
        self,
        state,
    ):
        primary_regime = (
            self.detect_primary_regime(
                state
            )
        )

        trend_regime = (
            self.classify_trend(
                state.trend_score
            )
        )

        volatility_regime = (
            self.classify_volatility(
                state.volatility_score
            )
        )

        risk_regime = (
            self.classify_risk(
                state.risk_sentiment_score
            )
        )

        event_regime = (
            self.classify_event_risk(
                state.event_risk_score
            )
        )

        regime_score = (
            self.calculate_regime_score(
                state
            )
        )

        return {
            "primary_regime":
                primary_regime,

            "regime_score":
                round(
                    regime_score,
                    3,
                ),

            "trend":
                trend_regime,

            "volatility":
                volatility_regime,

            "risk":
                risk_regime,

            "event_risk":
                event_regime,

            "raw_state": {
                "trend_score":
                    state.trend_score,

                "volatility_score":
                    state.volatility_score,

                "momentum_score":
                    state.momentum_score,

                "volume_score":
                    state.volume_score,

                "event_risk_score":
                    state.event_risk_score,

                "risk_sentiment_score":
                    state.risk_sentiment_score,
            },
        }


if __name__ == "__main__":

    engine = MarketRegimeEngine()

    # Synthetic test scenario.
    # These values are NOT live market data.

    state = MarketState(
        trend_score=0.72,
        volatility_score=0.35,
        momentum_score=0.65,
        volume_score=0.40,
        event_risk_score=0.20,
        risk_sentiment_score=0.55,
    )

    result = engine.analyze(
        state
    )

    print()
    print(
        "MARKET REGIME ENGINE TEST"
    )
    print("=" * 50)

    print(
        "Primary Regime:",
        result["primary_regime"],
    )

    print(
        "Regime Score:",
        result["regime_score"],
    )

    print(
        "Trend:",
        result["trend"],
    )

    print(
        "Volatility:",
        result["volatility"],
    )

    print(
        "Risk:",
        result["risk"],
    )

    print(
        "Event Risk:",
        result["event_risk"],
    )

    print(
        "Raw State:",
        result["raw_state"],
    )
