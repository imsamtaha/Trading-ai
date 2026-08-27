import unittest

from app.intelligence.reaction import MarketReactionEngine


class TestMarketReactionEngine(unittest.TestCase):

    def test_event_reaction(self):
        engine = MarketReactionEngine()

        candles = [
            {"open_time": 600000, "close": 100.0},
            {"open_time": 60000000, "close": 101.0},
            {"open_time": 120000, "close": 102.0},
            {"open_time": 180000, "close": 103.0},
            {"open_time": 240000, "close": 104.0},
            {"open_time": 300000, "close": 105.0},
            {"open_time": 360000, "close": 106.0},
            {"open_time": 420000, "close": 107.0},
            {"open_time": 480000, "close": 108.0},
            {"open_time": 540000, "close": 109.0},
            {"open_time": 600000000, "close": 110.0},
        ]

        result = engine.analyze(300, candles)

        print("\nREACTION TEST:")
        print("Status:", result["status"])
        print("Event price:", result["event_price"])
        print("Event candle:", result["event_candle_index"])
        print("Reactions:", result["reactions"])

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["event_price"], 105.0)
        self.assertEqual(result["event_candle_index"], 5)
        self.assertTrue(result["reactions"])


if __name__ == "__main__":
    unittest.main()
