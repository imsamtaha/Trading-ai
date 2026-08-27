import unittest

from app.intelligence.regime.engine import MarketRegimeEngine, MarketState
from app.intelligence.decision.engine import UnifiedDecisionEngine, DecisionInput


class TestIntelligencePipeline(unittest.TestCase):

    def test_bull_pipeline(self):
        state = MarketState(
            trend_score=0.90,
            momentum_score=0.90,
            volume_score=0.90,
            volatility_score=0.05,
            event_risk_score=0.05,
            risk_sentiment_score=0.10,
        )

        regime_engine = MarketRegimeEngine()
        regime = regime_engine.analyze(state)

        self.assertEqual(regime["primary_regime"], "BULL_TREND")
        self.assertEqual(regime["trend"], "BULL_TREND")

        decision_data = DecisionInput(
            technical_score=0.90,
            macro_score=0.80,
            news_score=0.80,
            geopolitical_score=0.80,
            cross_asset_score=0.80,
            reaction_score=0.80,
            regime=regime["primary_regime"],
            conflict_score=0.05,
            volatility_score=state.volatility_score,
            event_risk_score=state.event_risk_score,
        )

        decision = UnifiedDecisionEngine().analyze(decision_data)

        self.assertEqual(decision["decision"], "BUY")
        self.assertEqual(decision["bias"], "BULLISH")
        self.assertGreater(decision["confidence"], 0)

        print("\nPIPELINE TEST:")
        print("Regime:", regime["primary_regime"])
        print("Decision:", decision["decision"])
        print("Confidence:", decision["confidence"])
        print("Risk:", decision["risk_level"])


if __name__ == "__main__":
    unittest.main()
