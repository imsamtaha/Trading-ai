from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import AgentStatus, Signal


class SentimentAgent(BaseAgent):
    name = "sentiment"

    def evaluate(self, snapshot):
        started = perf_counter()
        if snapshot.sentiment is None:
            return self._verdict(snapshot, started=started, status=AgentStatus.UNAVAILABLE, signal=Signal.NEUTRAL, blockers=("sentiment data unavailable",), fresh=False, quality_score=0.0)
        bias = str(snapshot.sentiment.get("bias", "neutral")).lower()
        signal = Signal.LONG if bias == "bullish" else Signal.SHORT if bias == "bearish" else Signal.NEUTRAL
        score = abs(float(snapshot.sentiment.get("score", 0.0) or 0.0))
        return self._verdict(snapshot, started=started, signal=signal, confidence=min(0.8, 0.4 + score / 2), evidence=(f"bias:{bias}", f"score:{score:.2f}"))
