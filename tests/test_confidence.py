import unittest

from app.intelligence.confidence import SignalQualityEngine


class TestSignalQualityEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SignalQualityEngine()

    def test_mixed_signal_is_not_zero_information(self):
        result = self.engine.evaluate(
            {"score": 42.34, "conflict_score": 0.3413, "event_risk_score": 0.0, "volatility_score": 0.0},
            "WEAK",
        )
        self.assertGreater(result["directional_strength"], 0)
        self.assertGreater(result["evidence_quality"], 0)
        self.assertGreater(result["execution_confidence"], 0)
        self.assertIn(result["signal_quality"], {"VERY_LOW", "LOW", "MEDIUM", "HIGH"})

    def test_strong_aligned_signal_scores_high(self):
        result = self.engine.evaluate(
            {"score": 82.0, "conflict_score": 0.05, "event_risk_score": 0.05, "volatility_score": 0.05},
            "STRONG",
        )
        self.assertGreater(result["directional_strength"], 60)
        self.assertGreater(result["execution_confidence"], 55)


if __name__ == "__main__":
    unittest.main()
