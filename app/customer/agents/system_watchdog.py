from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import AgentStatus, Signal


class SystemWatchdog(BaseAgent):
    name = "system_watchdog"

    def evaluate(self, snapshot):
        started = perf_counter()
        blockers = []
        fresh = not self._stale(snapshot)
        if not fresh:
            blockers.append("stale market feed")
        if snapshot.system.get("connector_ok") is not True:
            blockers.append("connector unavailable")
        status = AgentStatus.DEGRADED if blockers else AgentStatus.OK
        return self._verdict(snapshot, started=started, status=status, signal=Signal.WAIT if blockers else Signal.NEUTRAL, confidence=1.0 if not blockers else 0.0, evidence=(f"latency_ms:{snapshot.system.get('latency_ms', 0)}",), blockers=tuple(blockers), fresh=fresh, quality_score=1.0 if not blockers else 0.0)
