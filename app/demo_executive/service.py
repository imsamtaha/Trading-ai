from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

class DemoExecutiveError(RuntimeError):
    pass


class DemoExecutiveService:
    def __init__(self, repository: Any, mt5_service: Any) -> None:
        self.repository = repository
        self.mt5_service = mt5_service
        self._active: dict[str, bool] = {}

    def _plan(self, user_id: str) -> str:
        return str(self.repository.get_subscription(user_id).get("plan", "FREE")).upper()

    @staticmethod
    def _decision(symbol: dict[str, Any] | None) -> str:
        if not symbol:
            return "WAIT"
        if str(symbol.get("risk_level", "LOW")).upper() in {"HIGH", "CRITICAL"}:
            return "WAIT"
        confidence = float(symbol.get("confidence", 0.0) or 0.0)
        trend = str(symbol.get("trend", "NEUTRAL")).upper()
        if confidence >= 70 and trend == "BULLISH":
            return "SIMULATE_BUY"
        if confidence >= 70 and trend == "BEARISH":
            return "SIMULATE_SELL"
        return "WAIT"

    def start(self, user_id: str) -> dict[str, Any]:
        plan = self._plan(user_id)
        dashboard = self.mt5_service.get_dashboard_state(user_id)
        if not dashboard.get("connected") or str((dashboard.get("account") or {}).get("account_type", "")).upper() != "DEMO":
            raise DemoExecutiveError("Connect an MT5 Demo account first.")
        symbol = (dashboard.get("symbols") or [None])[0]
        decision = self._decision(symbol)
        event = {
            "symbol": (symbol or {}).get("canonical_symbol") or (symbol or {}).get("symbol"),
            "decision": decision,
            "reason": "Deterministic demo-only ATLAS simulation.",
            "context": symbol or {},
            "simulation_only": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.repository.add_executive_event(user_id, event)
        self._active[user_id] = True
        return {"active": True, "plan": plan, "decision": decision, "simulation_only": True}

    def stop(self, user_id: str) -> dict[str, Any]:
        was_active = bool(self._active.get(user_id, False))
        self._active[user_id] = False
        if was_active:
            self.repository.add_executive_event(user_id, {
                "symbol": None,
                "decision": "CLOSE_SIMULATION",
                "reason": "Demo Executive stopped by the authenticated user.",
                "context": {},
                "simulation_only": True,
                "created_at": datetime.now(UTC).isoformat(),
            })
        return {"active": False, "simulation_only": True}

    def status(self, user_id: str) -> dict[str, Any]:
        plan = str(self.repository.get_subscription(user_id).get("plan", "FREE")).upper()
        return {"active": bool(self._active.get(user_id, False)), "plan": plan, "simulation_only": True}

    def events(self, user_id: str) -> list[dict[str, Any]]:
        return self.repository.list_executive_events(user_id)
