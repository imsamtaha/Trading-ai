from dataclasses import dataclass


@dataclass
class DecisionInput:
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

    def clamp(self, value, low=-1.0, high=1.0):
        return max(
            low,
            min(high, float(value)),
        )

    def regime_score(self, regime):

        mapping = {
            "BULL_TREND": 0.70,
            "BEAR_TREND": -0.70,
            "RISK_ON": 0.40,
            "RISK_OFF": -0.40,
            "SIDEWAYS": 0.0,
            "TRANSITION": 0.0,
            "HIGH_VOLATILITY": 0.0,
            "LOW_VOLATILITY": 0.0,
            "EVENT_DRIVEN": 0.0,
        }

        return mapping.get(
            regime,
            0.0,
        )

    def calculate_directional_score(
        self,
        data,
    ):

        values = {
            "technical":
                self.clamp(
                    data.technical_score
                ),

            "macro":
                self.clamp(
                    data.macro_score
                ),

            "news":
                self.clamp(
                    data.news_score
                ),

            "geopolitical":
                self.clamp(
                    data.geopolitical_score
                ),

            "cross_asset":
                self.clamp(
                    data.cross_asset_score
                ),

            "reaction":
                self.clamp(
                    data.reaction_score
                ),

            "regime":
                self.regime_score(
                    data.regime
                ),

            "risk":
                self.clamp(
                    (
                        data.macro_score
                        + data.cross_asset_score
                    ) / 2
                ),
        }

        score = 0.0

        for name, weight in self.WEIGHTS.items():

            score += (
                values[name]
                * weight
            )

        return self.clamp(score)

    def calculate_conflict_penalty(
        self,
        conflict_score,
    ):

        conflict_score = max(
            0.0,
            min(
                1.0,
                float(conflict_score),
            ),
        )

        return conflict_score * 0.35

    def calculate_event_penalty(
        self,
        event_risk_score,
    ):

        event_risk_score = max(
            0.0,
            min(
                1.0,
                float(event_risk_score),
            ),
        )

        return event_risk_score * 0.25

    def calculate_volatility_penalty(
        self,
        volatility_score,
    ):

        volatility_score = max(
            0.0,
            min(
                1.0,
                float(volatility_score),
            ),
        )

        return volatility_score * 0.20

    def calculate_confidence(
        self,
        directional_score,
        conflict_score,
        event_risk_score,
        volatility_score,
    ):

        directional_strength = abs(
            directional_score
        )

        confidence = (
            directional_strength
            * 100
        )

        confidence -= (
            self.calculate_conflict_penalty(
                conflict_score
            )
            * 100
        )

        confidence -= (
            self.calculate_event_penalty(
                event_risk_score
            )
            * 100
        )

        confidence -= (
            self.calculate_volatility_penalty(
                volatility_score
            )
            * 100
        )

        return round(
            max(
                0.0,
                min(
                    100.0,
                    confidence,
                ),
            ),
            2,
        )

    def determine_action(
        self,
        directional_score,
        confidence,
        conflict_score,
        event_risk_score,
    ):
        """
        Conservative decision gate.

        The engine does not trade merely because the market bias
        is bullish/bearish. It requires sufficient confidence,
        directional strength, and acceptable event/conflict risk.

        This is for paper-trading/testing until validated by
        historical out-of-sample results.
        """

        # 1. Severe information conflict
        if conflict_score >= 0.45:
            return "WAIT"

        # 2. Major event risk
        if event_risk_score >= 0.80:
            return "WAIT"

        # 3. Insufficient confidence
        if confidence < 55:
            return "WAIT"

        # 4. Weak directional evidence
        if -0.20 < directional_score < 0.20:
            return "WAIT"

        # 5. Strong bullish setup
        if directional_score >= 0.20:
            return "BUY"

        # 6. Strong bearish setup
        if directional_score <= -0.20:
            return "SELL"

        return "WAIT"


    def risk_level(
            self,
            conflict_score,
            event_risk_score,
            volatility_score,
        ):
            risk = (
                conflict_score * 0.40
                + event_risk_score * 0.35
                + volatility_score * 0.25
            )
    
            if risk >= 0.70:
                return "EXTREME"
    
            if risk >= 0.50:
                return "HIGH"
    
            if risk >= 0.30:
                return "MEDIUM"
    
            return "LOW"
    
    def analyze(
        self,
        data,
        ):
    
            directional_score = (
                self.calculate_directional_score(
                    data
                )
            )
        
            confidence = (
                self.calculate_confidence(
                    directional_score,
                    data.conflict_score,
                    data.event_risk_score,
                    data.volatility_score,
                )
            )
        
            action = self.determine_action(
                directional_score,
                confidence,
                data.conflict_score,
                data.event_risk_score,
            )
        
            risk = self.risk_level(
                data.conflict_score,
                data.event_risk_score,
                data.volatility_score,
            )
        
            if directional_score > 0:
                bias = "BULLISH"
        
            elif directional_score < 0:
                bias = "BEARISH"
        
            else:
                bias = "NEUTRAL"
        
            return {
                "decision": action,
                "bias": bias,
                "directional_score": round(
                    directional_score,
                    4,
                ),
                "confidence": confidence,
                "risk_level": risk,
                "regime": data.regime,
                "conflict_score": data.conflict_score,
                "event_risk_score":
                    data.event_risk_score,
                "volatility_score":
                    data.volatility_score,
            }
        
        
if __name__ == "__main__":

    engine = UnifiedDecisionEngine()

    # Synthetic scenario.
    # This is ONLY a software test.

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

    result = engine.analyze(
        market
    )

    print()
    print(
        "UNIFIED DECISION ENGINE TEST"
    )
    print("=" * 55)

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )
