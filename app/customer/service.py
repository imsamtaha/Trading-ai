from __future__ import annotations

from collections import defaultdict

from app.customer.repository import SupabaseCustomerAccountRepository
from app.customer.realtime.runtime import MT5DemoRuntime


class CustomerAccessError(PermissionError):
    pass


class CustomerService:
    def __init__(self, *, repository=None, demo_runtime=None):
        self.repository = repository
        self.demo_runtime = demo_runtime
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

    def register_account(self, customer_id: str, account_id: str, *, tier: str, mode: str = "LIVE_DEMO", auth_subject: str | None = None, **metadata):
        key = self._key(customer_id, account_id)
        row = {
            "customer_id": customer_id, "account_id": account_id, "tier": tier, "mode": mode,
            "auth_subject": auth_subject or customer_id,
            "broker": metadata.get("broker", "FXPRO"),
            "broker_login": metadata.get("broker_login"),
            "broker_server": metadata.get("broker_server"),
        }
        if self.repository is not None:
            row = dict(self.repository.upsert_account(row))
        self.accounts[key] = row
        return row

    def _load_account(self, customer_id: str, account_id: str):
        if self.repository is None:
            return None
        row = self.repository.get_account(customer_id, account_id)
        if row:
            self.accounts[self._key(customer_id, account_id)] = dict(row)
        return row

    def authorize(self, customer_id: str, account_id: str, *, auth_subject: str | None = None):
        key = self._key(customer_id, account_id)
        account = self.accounts.get(key) or self._load_account(customer_id, account_id)
        if account:
            if auth_subject is not None and str(account.get("auth_subject")) != str(auth_subject):
                raise CustomerAccessError("authenticated user does not own this customer account")
            return account
        if any(aid == account_id for _, aid in self.accounts):
            raise CustomerAccessError("account does not belong to customer")
        raise KeyError("account not found")

    def accounts_for_subject(self, auth_subject: str):
        rows = []
        if self.repository is not None:
            rows = self.repository.list_accounts_by_subject(auth_subject)
            for row in rows:
                self.accounts[self._key(row["customer_id"], row["account_id"])] = dict(row)
        else:
            rows = [dict(row) for row in self.accounts.values() if str(row.get("auth_subject")) == str(auth_subject)]
        for row in rows:
            row.pop("auth_subject", None)
        return rows

    def account(self, customer_id: str, account_id: str):
        account = dict(self.authorize(customer_id, account_id)); account.pop("auth_subject", None); return account

    def add_position(self, customer_id: str, account_id: str, position: dict):
        self.authorize(customer_id, account_id); self.positions[self._key(customer_id, account_id)].append(dict(position))

    def list_positions(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id); return list(self.positions[self._key(customer_id, account_id)])

    def add_alert(self, customer_id: str, account_id: str, alert: dict):
        self.authorize(customer_id, account_id); self.alerts[self._key(customer_id, account_id)].append(dict(alert))

    def list_alerts(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id); return list(self.alerts[self._key(customer_id, account_id)])

    def add_decision(self, customer_id: str, account_id: str, decision: dict):
        self.authorize(customer_id, account_id); self.decisions[self._key(customer_id, account_id)].append(dict(decision))

    def latest_decision(self, customer_id: str, account_id: str):
        self.authorize(customer_id, account_id); rows = self.decisions[self._key(customer_id, account_id)]
        return dict(rows[-1]) if rows else {"trace_id": None, "decision": "WAIT", "confidence": 0.0}

    def add_audit(self, customer_id: str, account_id: str, trace_id: str, event: dict):
        self.authorize(customer_id, account_id)
        self.audit[trace_id].append({"customer_id": customer_id, "account_id": account_id, "trace_id": trace_id, **dict(event)})

    def audit_trace(self, customer_id: str, account_id: str, trace_id: str):
        self.authorize(customer_id, account_id)
        rows = [r for r in self.audit.get(trace_id, []) if r["customer_id"] == customer_id and r["account_id"] == account_id]
        if not rows: raise KeyError("trace not found")
        return [dict(r) for r in rows]

    def start_demo_cycle(self, customer_id: str, account_id: str, *, symbol: str = "EURUSD", timeframe: str = "5m", demo_volume: float = 0.1, requested_risk_pct: float = 1.0):
        self.authorize(customer_id, account_id)
        runtime = self.demo_runtime or MT5DemoRuntime()
        result = runtime.run(customer_id=customer_id, account_id=account_id, symbol=symbol.upper(), timeframe=timeframe, demo_volume=demo_volume, requested_risk_pct=requested_risk_pct)
        trace_id = str(result.get("trace_id") or "")
        self.add_decision(customer_id, account_id, {
            "trace_id": trace_id, "decision": result.get("decision", "WAIT"),
            "confidence": float(result.get("confidence", 0.0) or 0.0), "status": result.get("status"),
        })
        broker_result = ((result.get("execution") or {}).get("broker_result") or {})
        if result.get("status") == "EXECUTED" and broker_result.get("ticket") is not None:
            self.add_position(customer_id, account_id, broker_result)
        if result.get("notification"):
            self.add_alert(customer_id, account_id, result["notification"])
        self.agent_status[self._key(customer_id, account_id)] = {"status": "READY", "agents": list(result.get("agents") or [])}
        self.rescue[self._key(customer_id, account_id)] = {"status": "ACTIVE", "action": result.get("rescue", "HOLD")}
        if trace_id:
            self.add_audit(customer_id, account_id, trace_id, {"event": "CUSTOMER_CYCLE_RESULT", "status": result.get("status")})
        return result


customer_service = CustomerService(repository=SupabaseCustomerAccountRepository.from_env())
