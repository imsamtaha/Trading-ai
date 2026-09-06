import unittest

from app.intelligence.context import build_mtf_context


class TestMTFContext(unittest.TestCase):
    def test_weighted_context_and_conflict(self):
        results = {
            "5m": {"technical": {"trend": "bullish", "momentum": "bullish", "macd_signal": "bullish"}, "structure": {"structure": "bullish"}, "signal": {"score": 70}},
            "15m": {"technical": {"trend": "bullish", "momentum": "bullish", "macd_signal": "bullish"}, "structure": {"structure": "bullish"}, "signal": {"score": 70}},
            "30m": {"technical": {"trend": "bullish", "momentum": "bullish", "macd_signal": "bullish"}, "structure": {"structure": "bullish"}, "signal": {"score": 80}},
            "1h": {"technical": {"trend": "bullish", "momentum": "bullish", "macd_signal": "bullish"}, "structure": {"structure": "bullish"}, "signal": {"score": 80}},
        }
        result = build_mtf_context(results, {"5m": 0.15, "15m": 0.20, "30m": 0.25, "1h": 0.40})
        self.assertGreater(result["mtf_score"], 0.4)
        self.assertEqual(result["bias"], "BULLISH")
        self.assertLess(result["conflict_score"], 0.2)


if __name__ == "__main__":
    unittest.main()
