from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.customer.agents.trader import TradeIntent
from app.customer.contracts import Mode


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    mode: Mode
    trace_id: str
    customer_id: str
    account_id: str
    broker_result: dict[str, Any] | None = None
    reason: str | None = None


class DemoAdapter:
    def __init__(self, broker):
        self.broker = broker

    def execute(self, intent: TradeIntent, risk: dict[str, Any], *, trace_id: str) -> ExecutionResult:
        if intent.mode is not Mode.LIVE_DEMO:
            return ExecutionResult("BLOCKED", Mode.LIVE_DEMO, trace_id, intent.customer_id, intent.account_id, reason="intent is not LIVE_DEMO")
        if risk.get("approved") is not True:
            return ExecutionResult("BLOCKED", Mode.LIVE_DEMO, trace_id, intent.customer_id, intent.account_id, reason=str(risk.get("reason") or "risk rejected"))
        if getattr(self.broker, "connected", False) is not True:
            return ExecutionResult("BLOCKED", Mode.LIVE_DEMO, trace_id, intent.customer_id, intent.account_id, reason="MT5 connector is not connected")
        volume = float(risk.get("volume", 0.0) or 0.0)
        if volume <= 0:
            return ExecutionResult("BLOCKED", Mode.LIVE_DEMO, trace_id, intent.customer_id, intent.account_id, reason="demo volume is required")
        result = self.broker.market_order(
            symbol=intent.symbol,
            direction=intent.direction,
            volume=volume,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            comment=f"ATLAS-DEMO-{trace_id}"[:31],
        )
        return ExecutionResult("EXECUTED", Mode.LIVE_DEMO, trace_id, intent.customer_id, intent.account_id, broker_result=dict(result))
