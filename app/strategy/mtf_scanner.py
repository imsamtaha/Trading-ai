from __future__ import annotations

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles


class MTFScanner:
    """Run the existing analysis stack across Trading Hub execution timeframes."""

    def __init__(self, market_data, timeframes=("5m", "15m", "30m", "1h"), candle_limit=200):
        self.market_data = market_data
        self.timeframes = tuple(timeframes)
        self.candle_limit = candle_limit

    def scan(self, symbol: str) -> dict:
        frames = {}
        errors = {}

        for timeframe in self.timeframes:
            try:
                market = self.market_data.candles(symbol, timeframe, self.candle_limit)
                candles = market["candles"]
                if len(candles) < 20:
                    raise ValueError("At least 20 candles are required")
                frames[timeframe] = {
                    "market": market,
                    "technical": analyze_candles(candles),
                    "structure": analyze_structure(candles),
                }
            except Exception as exc:
                errors[timeframe] = str(exc)

        return {
            "symbol": symbol.upper(),
            "timeframes": frames,
            "errors": errors,
            "complete": not errors and len(frames) == len(self.timeframes),
        }
