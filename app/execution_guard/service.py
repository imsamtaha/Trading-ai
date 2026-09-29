from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import uuid4

from .models import CouncilDecision, GuardResult, TradeDraft


class ExecutionGuardService:
    def __init__(self, repository: Any, mt5_service: Any, *, confidence_threshold: float = 70.0,
                 freshness_seconds: int = 300, clock: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self.mt5_service = mt5_service
        self.confidence_threshold = confidence_threshold
        self.freshness_seconds = freshness_seconds
        self.clock = clock or (lambda: datetime.now(UTC))

    def _events(self, user_id: str) -> list[dict[str, Any]]:
        getter = getattr(self.repository, "list_execution_guard_events", None)
        if callable(getter):
            return getter(user_id)
        return [e for e in getattr(self.repository, "events", []) if e.get("user_id") == user_id]

    def _record(self, user_id: str, decision_id: str, status: str, reason: str | None = None,
                draft_id: str | None = None) -> None:
        self.repository.add_execution_guard_event(user_id, {
            "decision_id": decision_id, "status": status, "reason": reason,
            "draft_id": draft_id, "created_at": self.clock().isoformat(),
        })

    def _block(self, user_id: str, decision: CouncilDecision, reason: str) -> GuardResult:
        self._record(user_id, decision.decision_id, "BLOCKED", reason)
        return GuardResult(decision_id=decision.decision_id, status="BLOCKED", reason=reason)

    def _duplicate(self, user_id: str, decision_id: str) -> bool:
        return any(e.get("decision_id") == decision_id for e in self._events(user_id))

    @staticmethod
    def _price_for(dashboard: dict[str, Any], symbol: str) -> float | None:
        for item in dashboard.get("symbols") or []:
            if str(item.get("symbol") or item.get("canonical_symbol")) == symbol:
                value = item.get("price")
                return float(value) if isinstance(value, (int, float)) else None
        return None

    def evaluate(self, user_id: str, decision: CouncilDecision) -> GuardResult:
        if self._duplicate(user_id, decision.decision_id):
            return GuardResult(decision_id=decision.decision_id, status="BLOCKED", reason="Duplicate decision.")
        if decision.direction == "WAIT":
            return self._block(user_id, decision, "Council decision is WAIT.")
        if decision.confidence < self.confidence_threshold:
            return self._block(user_id, decision, "Council confidence is below the execution threshold.")
        now = self.clock()
        stamp = decision.timestamp if decision.timestamp.tzinfo else decision.timestamp.replace(tzinfo=UTC)
        if now - stamp > timedelta(seconds=self.freshness_seconds) or stamp > now + timedelta(seconds=30):
            return self._block(user_id, decision, "Council decision is stale or future-dated.")
        dashboard = self.mt5_service.get_dashboard_state(user_id)
        if not dashboard.get("connected"):
            return self._block(user_id, decision, "MT5 account is not connected.")
        account = dashboard.get("account") or {}
        mode = str(account.get("account_type", "")).upper()
        if mode not in {"DEMO", "REAL"}:
            return self._block(user_id, decision, "Unsupported MT5 account mode.")
        price = self._price_for(dashboard, decision.symbol)
        if price is None:
            return self._block(user_id, decision, "Fresh market price is unavailable.")
        if decision.direction == "BUY" and not (decision.stop_loss < price < decision.take_profit):
            return self._block(user_id, decision, "BUY requires SL < market price < TP.")
        if decision.direction == "SELL" and not (decision.take_profit < price < decision.stop_loss):
            return self._block(user_id, decision, "SELL requires TP < market price < SL.")

        if mode == "DEMO":
            state = self.mt5_service.manual_trading_state(user_id)
            if not state.get("active"):
                return self._block(user_id, decision, "Demo execution is disabled.")
            result = self.mt5_service.place_manual_order(user_id, {
                "request_id": decision.decision_id, "account_type": "DEMO", "symbol": decision.symbol,
                "direction": decision.direction, "volume": decision.volume,
                "stop_loss": decision.stop_loss, "take_profit": decision.take_profit, "confirmed": True,
            })
            if result.get("status") != "FILLED":
                return self._block(user_id, decision, "Broker did not confirm a demo fill.")
            self._record(user_id, decision.decision_id, "EXECUTED")
            return GuardResult(decision_id=decision.decision_id, status="EXECUTED")

        draft_id = f"draft-{uuid4().hex[:16]}"
        draft = TradeDraft(
            draft_id=draft_id, user_id=user_id, decision_id=decision.decision_id,
            account_masked=str(account.get("account_masked", "")), account_type="REAL",
            symbol=decision.symbol, direction=decision.direction,
            volume=decision.volume, stop_loss=decision.stop_loss, take_profit=decision.take_profit,
            confidence=decision.confidence, rationale=decision.rationale,
            expires_at=self.clock() + timedelta(minutes=2),
            council_evidence=decision.model_dump(mode="json"), risk_result={"status": "READY"},
        )
        self.repository.save_trade_draft(user_id, draft.model_dump(mode="json"))
        self._record(user_id, decision.decision_id, "WAITING_CONFIRMATION", draft_id=draft_id)
        return GuardResult(decision_id=decision.decision_id, status="WAITING_CONFIRMATION", draft_id=draft_id)

    def confirm(self, user_id: str, draft_id: str) -> dict[str, Any]:
        draft = self.repository.get_trade_draft(user_id, draft_id)
        if not draft:
            raise ValueError("Trade draft not found for this user.")
        if draft.get("status") != "WAITING_CONFIRMATION":
            raise ValueError("Trade draft is no longer confirmable.")
        expires_at = datetime.fromisoformat(str(draft["expires_at"]).replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if self.clock() >= expires_at:
            self.repository.mark_trade_draft(user_id, draft_id, "EXPIRED")
            raise ValueError("Trade draft has expired.")
        dashboard = self.mt5_service.get_dashboard_state(user_id)
        account = dashboard.get("account") or {}
        if not dashboard.get("connected") or str(account.get("account_type", "")).upper() != "REAL":
            raise ValueError("Connected MT5 account is not the required REAL account.")
        if str(account.get("account_masked", "")) != str(draft.get("account_masked", "")):
            raise ValueError("MT5 account changed before confirmation.")
        raise ValueError("Live broker execution is disabled for this deployment.")

    def status(self, user_id: str) -> dict[str, Any]:
        events = self._events(user_id)
        latest = events[-1] if events else None
        return {"status": (latest or {}).get("status", "READY"), "last_event": latest}

    def events(self, user_id: str) -> list[dict[str, Any]]:
        return self._events(user_id)
