from __future__ import annotations

from uuid import uuid4

from app.customer.agents.capital_guardian import evaluate_capital
from app.customer.agents.coordinator import coordinate
from app.customer.agents.financial_monitor import FinancialMonitor
from app.customer.agents.news import NewsAgent
from app.customer.agents.regime import RegimeAgent
from app.customer.agents.rescue import RescueAgent
from app.customer.agents.sentiment import SentimentAgent
from app.customer.agents.system_watchdog import SystemWatchdog
from app.customer.agents.technical import TechnicalAgent
from app.customer.agents.trader import TraderAgent
from app.customer.audit import AuditStore
from app.customer.contracts import AgentStatus, Decision, Mode
from app.customer.execution.mode_router import ModeRouter
from app.customer.monitoring.notifications import build_notification
from app.customer.monitoring.position_monitor import PositionMonitor
from app.risk.manager import calculate_risk


class CustomerRealtimeCycle:
    def __init__(self, demo_adapter, *, audit_store: AuditStore | None = None):
        self.audit_store = audit_store or AuditStore()
        self.router = ModeRouter(demo_adapter)
        self.agents = [TechnicalAgent(), NewsAgent(), SentimentAgent(), RegimeAgent(), FinancialMonitor(), SystemWatchdog()]
        self.trader = TraderAgent()
        self.monitor = PositionMonitor(RescueAgent(), audit_store=self.audit_store)

    def _audit(self, snapshot, trace_id: str, event: str, **payload):
        self.audit_store.append({
            "event": event,
            "trace_id": trace_id,
            "customer_id": snapshot.customer_id,
            "account_id": snapshot.account_id,
            "mode": snapshot.mode.value,
            "snapshot_id": snapshot.snapshot_id,
            **payload,
        })

    def run(
        self,
        snapshot,
        *,
        stop_loss: float,
        take_profit: float,
        demo_volume: float,
        requested_risk_pct: float = 1.0,
        learned_weights: dict[str, float] | None = None,
        trace_id: str | None = None,
    ) -> dict:
        trace_id = trace_id or str(uuid4())
        self._audit(snapshot, trace_id, "SNAPSHOT")

        if snapshot.mode is not Mode.LIVE_DEMO:
            return {"status": "BLOCKED", "reason": "cycle requires LIVE_DEMO", "trace_id": trace_id}

        verdicts = [agent.evaluate(snapshot) for agent in self.agents]
        self._audit(snapshot, trace_id, "AGENTS", agents=[v.agent for v in verdicts])
        critical = [v for v in verdicts if v.agent in {"technical", "system_watchdog"} and v.status is not AgentStatus.OK]
        if critical:
            reason = "; ".join(b for v in critical for b in v.blockers) or "critical agent degraded"
            self._audit(snapshot, trace_id, "DECISION", decision="WAIT", reason=reason)
            return {"status": "BLOCKED", "reason": reason, "trace_id": trace_id, "decision": "WAIT"}

        decision = coordinate(snapshot, verdicts, weights=learned_weights)
        self._audit(snapshot, trace_id, "DECISION", decision=decision.decision.value, confidence=decision.confidence, blockers=list(decision.blockers))
        if decision.decision not in {Decision.BUY, Decision.SELL}:
            return {"status": "BLOCKED", "reason": "non-actionable decision", "trace_id": trace_id, "decision": decision.decision.value}

        capital = evaluate_capital(snapshot, requested_risk_pct=requested_risk_pct)
        self._audit(snapshot, trace_id, "CAPITAL", approved=capital.approved, blockers=list(capital.blockers))
        if not capital.approved:
            return {"status": "BLOCKED", "reason": "; ".join(capital.blockers), "trace_id": trace_id, "decision": decision.decision.value}

        entry = float(snapshot.market.get("ask") if decision.decision is Decision.BUY else snapshot.market.get("bid"))
        stop_distance = abs(float(stop_loss) - entry)
        target_distance = abs(float(take_profit) - entry)
        if stop_distance <= 0 or target_distance <= 0:
            return {"status": "BLOCKED", "reason": "invalid stop distance", "trace_id": trace_id, "decision": decision.decision.value}
        if decision.decision is Decision.BUY:
            stop_loss, take_profit = entry - stop_distance, entry + target_distance
        else:
            stop_loss, take_profit = entry + stop_distance, entry - target_distance
        intent = self.trader.build_intent(snapshot, decision, entry=entry, stop_loss=stop_loss, take_profit=take_profit)
        risk = calculate_risk(
            direction=intent.direction,
            entry=intent.entry,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            account_balance=float(snapshot.account.get("equity", 0.0) or 0.0),
            risk_percent=requested_risk_pct,
            open_risk_percent=float(snapshot.account.get("open_risk_pct", 0.0) or 0.0),
        )
        risk = dict(risk)
        risk["volume"] = float(demo_volume)
        self._audit(snapshot, trace_id, "RISK", approved=bool(risk.get("approved")), reason=risk.get("reason"))
        if risk.get("approved") is not True:
            return {"status": "BLOCKED", "reason": str(risk.get("reason")), "trace_id": trace_id, "decision": decision.decision.value}

        execution = self.router.execute_demo(intent, risk, trace_id=trace_id)
        execution_payload = {
            "status": execution.status,
            "mode": execution.mode.value,
            "trace_id": execution.trace_id,
            "customer_id": execution.customer_id,
            "account_id": execution.account_id,
            "broker_result": execution.broker_result,
            "reason": execution.reason,
        }
        self._audit(snapshot, trace_id, "EXECUTION", status=execution.status, reason=execution.reason)
        if execution.status != "EXECUTED":
            return {"status": "BLOCKED", "reason": execution.reason, "trace_id": trace_id, "decision": decision.decision.value, "execution": execution_payload}

        broker_result = execution.broker_result or {}
        position = {
            "ticket": broker_result.get("ticket"),
            "symbol": intent.symbol,
            "direction": intent.direction,
            "entry": intent.entry,
            "unrealized_loss_pct": 0.0,
        }
        rescue = self.monitor.evaluate(position, snapshot, trace_id=trace_id)
        self._audit(snapshot, trace_id, "RESCUE", action=rescue.action.value, reason=rescue.reason)
        notification = build_notification(snapshot, trace_id=trace_id, event="EXECUTION", payload={"status": execution.status, "ticket": broker_result.get("ticket"), "rescue": rescue.action.value})
        self._audit(snapshot, trace_id, "NOTIFICATION", event_type=notification["event"])
        return {
            "status": execution.status,
            "agents": [v.agent for v in verdicts],
            "agent_signals": {v.agent: v.signal.value for v in verdicts},
            "trace_id": trace_id,
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "execution": execution_payload,
            "rescue": rescue.action.value,
            "notification": notification,
        }
