from time import perf_counter

from app.customer.agents.base import BaseAgent
from app.customer.contracts import AgentStatus, Signal


class FinancialMonitor(BaseAgent):
    name = "financial"

    def evaluate(self, snapshot):
        started = perf_counter()
        equity = float(snapshot.account.get("equity", 0.0) or 0.0)
        balance = float(snapshot.account.get("balance", 0.0) or 0.0)
        drawdown = float(snapshot.account.get("drawdown_pct", 0.0) or 0.0)
        blockers = () if equity > 0 and balance > 0 else ("invalid account state",)
        status = AgentStatus.OK if not blockers else AgentStatus.DEGRADED
        return self._verdict(snapshot, started=started, status=status, signal=Signal.NEUTRAL, confidence=0.9 if not blockers else 0.0, evidence=(f"equity:{equity:.2f}", f"drawdown_pct:{drawdown:.2f}"), blockers=blockers, quality_score=1.0 if not blockers else 0.0)
