from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import AgentStatus, Signal


class NewsAgent(BaseAgent):
    name = "news"

    def evaluate(self, snapshot):
        started = perf_counter()
        if snapshot.news is None:
            return self._verdict(snapshot, started=started, status=AgentStatus.UNAVAILABLE, signal=Signal.NEUTRAL, blockers=("news data unavailable",), fresh=False, quality_score=0.0)
        impact = str(snapshot.news.get("impact", "unknown")).lower()
        bias = str(snapshot.news.get("bias", "neutral")).lower()
        signal = Signal.LONG if bias == "bullish" else Signal.SHORT if bias == "bearish" else Signal.NEUTRAL
        confidence = 0.7 if impact in {"high", "medium"} and signal is not Signal.NEUTRAL else 0.4
        return self._verdict(snapshot, started=started, signal=signal, confidence=confidence, evidence=(f"impact:{impact}", f"bias:{bias}"))
