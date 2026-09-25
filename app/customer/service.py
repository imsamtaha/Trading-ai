from __future__ import annotations

from collections import defaultdict
from uuid import uuid4


class CustomerAccessError(PermissionError):
    pass


class CustomerService:
    def __init__(self):
        self.reset()

    def reset(self):
        self.accounts = {}
        self.positions = defaultdict(list)
        self.alerts = defaultdict(list)
        self.decisions = defaultdict(list)
        self.audit = defaultdict(list)
        self.agent_status = defaultdict(lambda: {"status": "READY", "agents": []})
        self.rescue = defaultdict(lambda: {"status": "IDLE", "action": "HOLD"})

    @staticmethod
    def _key(customer_id: str, account_id: str):
        return customer_id, account_id

    def register_account(self, customer_id: str, account_id: str, *, tier: str, mode: str = "LIVE_DEMO"):
        key = self._key(customer_id, account_id)
        self.accounts[key] = {"customer_id": customer_id, "account_id": account_id, "tier": tier, "mode": mode}
        return self.accounts[key]

    def authorize(self, customer_id: str, account_id: str):
        key = self._key(customer_id, account_id)
        if key in self.accounts:
            return self.accounts[key]
        if any(aid == account_id for _, aid in self.accounts):
            raise CustomerAccessError("account does not belong to customer")
        raise KeyError("account not found")

    def account(self, customer_id: str, account_id: str):
        return dict(self.authorize(customer_id, account_id))

    def add_position(self, customer_id: str, account_id: str, position: dict):
        self.authorize(customer_id, account_id)
        self.positions[self._key(customer_id, account_id)].append(dict(position))

    def list_positions(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id)
        return list(self.positions[self._key(customer_id, account_id)])

    def add_alert(self, customer_id: str, account_id: str, alert: dict):
        self.authorize(customer_id, account_id)
        self.alerts[self._key(customer_id, account_id)].append(dict(alert))

    def list_alerts(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id)
        return list(self.alerts[self._key(customer_id, account_id)])

    def add_decision(self, customer_id: str, account_id: str, decision: dict):
        self.authorize(customer_id, account_id)
        self.decisions[self._key(customer_id, account_id)].append(dict(decision))

    def latest_decision(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id)
        rows = self.decisions[self._key(customer_id, account_id)]
        return dict(rows[-1]) if rows else {"trace_id": None, "decision": "WAIT", "confidence": 0.0}

    def add_audit(self, customer_id: str, account_id: str, trace_id: str, event: dict):
        self.authorize(customer_id, account_id)
        row = {"customer_id": customer_id, "account_id": account_id, "trace_id": trace_id, **dict(event)}
        self.audit[trace_id].append(row)

    def audit_trace(self, customer_id: str, account_id: str, trace_id: str):
        self.authorize(customer_id, account_id)
        rows = [r for r in self.audit.get(trace_id, []) if r["customer_id"] == customer_id and r["account_id"] == account_id]
        if not rows:
            raise KeyError("trace not found")
        return [dict(r) for r in rows]

    def start_demo_cycle(self, customer_id: str, account_id: str):
        account = self.authorize(customer_id, account_id)
        trace_id = str(uuid4())
        result = {"customer_id": customer_id, "account_id": account_id, "mode": "LIVE_DEMO", "trace_id": trace_id, "status": "READY"}
        self.add_audit(customer_id, account_id, trace_id, {"event": "DEMO_CYCLE_CREATED"})
        return result


customer_service = CustomerService()
