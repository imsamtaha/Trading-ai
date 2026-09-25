from __future__ import annotations

from app.customer.agents.rescue import RescueAgent
from app.customer.audit import AuditStore


class PositionMonitor:
    def __init__(self, rescue_agent: RescueAgent, *, audit_store: AuditStore | None = None):
        self.rescue_agent = rescue_agent
        self.audit_store = audit_store or AuditStore()

    def evaluate(self, position: dict, snapshot, *, trace_id: str):
        decision = self.rescue_agent.evaluate(position, snapshot)
        self.audit_store.append({
            "event": "RESCUE_DECISION",
            "trace_id": trace_id,
            "customer_id": snapshot.customer_id,
            "account_id": snapshot.account_id,
            "mode": snapshot.mode.value,
            "snapshot_id": snapshot.snapshot_id,
            "position_ticket": position.get("ticket"),
            "action": decision.action.value,
            "reason": decision.reason,
        })
        return decision
