from __future__ import annotations

from dataclasses import dataclass

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles


DEFAULT_TIMEFRAMES = ("5m", "15m", "30m", "1h")


@dataclass(frozen=True)
class MTFDecision:
    symbol: str
    consensus: str
    alignment_count: int
    total_timeframes: int
    frames: dict
    errors: dict

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "consensus": self.consensus,
            "alignment": f"{self.alignment_count}/{self.total_timeframes}",
            "timeframes": self.frames,
            "errors": self.errors,
            "complete": not self.errors and len(self.frames) == self.total_timeframes,
        }


class MTFSummaryEngine:
    """Summarize existing analysis across the Trading Hub execution timeframes."""

    def __init__(self, market_data, timeframes=DEFAULT_TIMEFRAMES, candle_limit=200):
        self.market_data = market_data
        self.timeframes = tuple(timeframes)
        self.candle_limit = candle_limit

    def analyze(self, symbol: str) -> MTFDecision:
        frames: dict[str, dict] = {}
        errors: dict[str, str] = {}

        for timeframe in self.timeframes:
            try:
                market = self.market_data.candles(symbol, timeframe, self.candle_limit)
                candles = market.get("candles", [])
                technical = analyze_candles(candles)
                structure = analyze_structure(candles)
                frames[timeframe] = {
                    "price": technical.get("price"),
                    "trend": technical.get("trend"),
                    "momentum": technical.get("momentum"),
                    "macd_signal": technical.get("macd_signal"),
                    "structure": structure.get("structure"),
                    "break_events": structure.get("break_events", []),
                    "liquidity_events": structure.get("liquidity_events", []),
                }
            except Exception as exc:
                errors[timeframe] = str(exc)

        directions = []
        for frame in frames.values():
            trend = frame.get("trend", "").lower()
            structure = frame.get("structure", "").lower()
            if trend == structure and trend in {"bullish", "bearish"}:
                directions.append(trend.upper())
            elif trend in {"bullish", "bearish"}:
                directions.append(trend.upper())

        bullish = directions.count("BULLISH")
        bearish = directions.count("BEARISH")
        consensus = "BULLISH" if bullish > bearish else "BEARISH" if bearish > bullish else "NEUTRAL"
        alignment = max(bullish, bearish) if directions else 0

        return MTFDecision(
            symbol=symbol.upper(),
            consensus=consensus,
            alignment_count=alignment,
            total_timeframes=len(self.timeframes),
            frames=frames,
            errors=errors,
        )
