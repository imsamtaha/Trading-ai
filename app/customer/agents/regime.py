from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import Signal


class RegimeAgent(BaseAgent):
    name = "regime"

    def evaluate(self, snapshot):
        started = perf_counter()
        volatility = float(snapshot.market.get("volatility", 0.0) or 0.0)
        trend = str(snapshot.market.get("trend", "unknown")).lower()
        regime = "volatile" if volatility >= 1.0 else "trending" if trend in {"bullish", "bearish"} else "ranging"
        signal = Signal.LONG if trend == "bullish" else Signal.SHORT if trend == "bearish" else Signal.NEUTRAL
        return self._verdict(snapshot, started=started, signal=signal, confidence=0.6, evidence=(f"regime:{regime}", f"volatility:{volatility:.2f}"))
