import unittest

from app.intelligence.regime.engine import MarketRegimeEngine, MarketState


class TestMarketRegimeEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MarketRegimeEngine()

    def test_bull_trend(self):
        state = MarketState(
            trend_score=0.90,
            momentum_score=0.90,
            volume_score=0.90,
            volatility_score=0.05,
            event_risk_score=0.05,
            risk_sentiment_score=0.10,
        )

        result = self.engine.detect_primary_regime(state)

        print("\nBULL TEST:", result)

        self.assertEqual(result, "BULL_TREND")

    def test_bear_trend(self):
        state = MarketState(
            trend_score=-0.90,
            momentum_score=-0.90,
            volume_score=-0.90,
            volatility_score=0.05,
            event_risk_score=0.05,
            risk_sentiment_score=-0.10,
        )

        result = self.engine.detect_primary_regime(state)

        print("\nBEAR TEST:", result)

        self.assertEqual(result, "BEAR_TREND")

    def test_range_market(self):
        state = MarketState(
            trend_score=0.0,
            momentum_score=0.0,
            volume_score=0.0,
            volatility_score=0.05,
            event_risk_score=0.05,
            risk_sentiment_score=0.0,
        )

        result = self.engine.detect_primary_regime(state)

        print("\nRANGE TEST:", result)

        self.assertEqual(result, "RANGE")


if __name__ == "__main__":
    unittest.main()
