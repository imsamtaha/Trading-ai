import unittest

from app.intelligence.decision.engine import (
    UnifiedDecisionEngine,
    DecisionInput,
)


class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = UnifiedDecisionEngine()

    def make_input(self, **overrides):
        values = dict(
            technical_score=0.0,
            macro_score=0.0,
            news_score=0.0,
            geopolitical_score=0.0,
            cross_asset_score=0.0,
            reaction_score=0.0,
            regime="RANGE",
            conflict_score=0.20,
            event_risk_score=0.20,
            volatility_score=0.25,
        )
        values.update(overrides)
        return DecisionInput(**values)

    def test_strong_buy(self):
        data = self.make_input(
            technical_score=0.95,
            macro_score=0.90,
            news_score=0.90,
            geopolitical_score=0.85,
            cross_asset_score=0.90,
            reaction_score=0.90,
            regime="BULL_TREND",
            conflict_score=0.05,
            event_risk_score=0.05,
            volatility_score=0.05,
        )

        result = self.engine.analyze(data)

        self.assertEqual(result["decision"], "BUY")
        self.assertEqual(result["bias"], "BULLISH")
        self.assertGreaterEqual(result["confidence"], 55)
        self.assertEqual(result["risk_level"], "LOW")

    def test_strong_sell(self):
        data = self.make_input(
            technical_score=-0.95,
            macro_score=-0.90,
            news_score=-0.90,
            geopolitical_score=-0.85,
            cross_asset_score=-0.90,
            reaction_score=-0.90,
            regime="BEAR_TREND",
            conflict_score=0.05,
            event_risk_score=0.05,
            volatility_score=0.05,
        )

        result = self.engine.analyze(data)

        self.assertEqual(result["decision"], "SELL")
        self.assertEqual(result["bias"], "BEARISH")
        self.assertGreaterEqual(result["confidence"], 55)
        self.assertEqual(result["risk_level"], "LOW")

    def test_uncertain_market_waits(self):
        data = self.make_input(
            technical_score=0.05,
            macro_score=0.00,
            news_score=0.02,
            geopolitical_score=-0.02,
            cross_asset_score=0.03,
            reaction_score=0.00,
            regime="RANGE",
            conflict_score=0.20,
            event_risk_score=0.20,
            volatility_score=0.25,
        )

        result = self.engine.analyze(data)

        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["confidence"], 0.0)

    def test_buy_sell_wait_directly(self):
        self.assertEqual(
            self.engine.determine_action(72.25, 72.25, 0.18, 0.15, "LOW"),
            "BUY",
        )

        self.assertEqual(
            self.engine.determine_action(27.75, 72.25, 0.18, 0.15, "LOW"),
            "SELL",
        )

        self.assertEqual(
            self.engine.determine_action(50.0, 70, 0.18, 0.15, "LOW"),
            "WAIT",
        )

    def test_risk_levels(self):
        self.assertEqual(
            self.engine.risk_level(0.05, 0.05, 0.05),
            "LOW",
        )

        self.assertEqual(
            self.engine.risk_level(0.50, 0.50, 0.50),
            "HIGH",
        )

        self.assertEqual(
            self.engine.risk_level(0.80, 0.80, 0.80),
            "EXTREME",
        )


if __name__ == "__main__":
    unittest.main()
