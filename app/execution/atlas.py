from __future__ import annotations

from math import isfinite
from dataclasses import dataclass
from typing import Any

from app.execution.mt5 import MT5Broker


@dataclass(frozen=True)
class ExecutionPolicy:
    enabled: bool = False
    min_confidence: float = 55.0
    max_risk_level: str = "MEDIUM"
    allow_buy: bool = True
    allow_sell: bool = True


class AtlasExecutionService:
    """Execution gate between ATLAS decisions and the broker adapter."""

    RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}

    def __init__(self, broker: MT5Broker | None = None, policy: ExecutionPolicy | None = None):
        self.broker = broker or MT5Broker()
        self.policy = policy or ExecutionPolicy()

    def gate(self, decision: dict[str, Any]) -> tuple[bool, str]:
        action = str(decision.get("decision", "WAIT")).upper()
        confidence = float(decision.get("confidence", 0.0))
        risk = str(decision.get("risk_level", "EXTREME")).upper()

        if not self.policy.enabled:
            return False, "LIVE_EXECUTION_DISABLED"
        if action not in {"BUY", "SELL"}:
            return False, "NO_TRADE_DECISION"
        if not isfinite(confidence) or confidence < self.policy.min_confidence:
            return False, "CONFIDENCE_BELOW_THRESHOLD"
        if self.RISK_ORDER.get(risk, 3) > self.RISK_ORDER[self.policy.max_risk_level]:
            return False, "RISK_LEVEL_BLOCKED"
        if action == "BUY" and not self.policy.allow_buy:
            return False, "BUY_DISABLED"
        if action == "SELL" and not self.policy.allow_sell:
            return False, "SELL_DISABLED"
        return True, "APPROVED"

    def execute(
        self,
        symbol: str,
        decision: dict[str, Any],
        volume: float,
        stop_loss: float,
        take_profit: float,
        *, max_cash_risk: float | None = None, expected_entry: float | None = None,
        max_entry_deviation: float | None = None, expected_account: dict | None = None,
    ) -> dict[str, Any]:
        approved, reason = self.gate(decision)
        if not approved:
            return {
                "status": "BLOCKED",
                "symbol": symbol,
                "reason": reason,
                "decision": decision.get("decision", "WAIT"),
            }

        bounds = {}
        if max_cash_risk is not None:
            bounds["max_cash_risk"] = max_cash_risk
        if expected_entry is not None:
            bounds.update(expected_entry=expected_entry, max_entry_deviation=max_entry_deviation)
        if expected_account is not None:
            bounds["expected_account"] = expected_account
        return self.broker.market_order(
            symbol=symbol,
            direction=str(decision["decision"]),
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment="ATLAS",
            **bounds,
        )

    def status(self) -> dict[str, Any]:
        return {
            "live_execution_enabled": self.policy.enabled,
            "min_confidence": self.policy.min_confidence,
            "max_risk_level": self.policy.max_risk_level,
            "mt5_dry_run": self.broker.config.dry_run,
        }

