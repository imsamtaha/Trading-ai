from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import AgentStatus, Signal


class TechnicalAgent(BaseAgent):
    name = "technical"

    def evaluate(self, snapshot):
        started = perf_counter()
        if self._stale(snapshot):
            return self._verdict(snapshot, started=started, status=AgentStatus.DEGRADED, signal=Signal.WAIT, blockers=("stale market data",), fresh=False, quality_score=0.0)
        trend = str(snapshot.market.get("trend", "")).lower()
        momentum = str(snapshot.market.get("momentum", "")).lower()
        if trend == "bullish" and momentum in {"positive", "bullish", "up"}:
            signal, confidence = Signal.LONG, 0.75
        elif trend == "bearish" and momentum in {"negative", "bearish", "down"}:
            signal, confidence = Signal.SHORT, 0.75
        else:
            signal, confidence = Signal.WAIT, 0.4
        return self._verdict(snapshot, started=started, signal=signal, confidence=confidence, evidence=(f"trend:{trend or 'unknown'}", f"momentum:{momentum or 'unknown'}"))
