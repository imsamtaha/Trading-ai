from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.risk.manager import calculate_risk


@dataclass(frozen=True)
class AutoExecutionConfig:
    enabled: bool = False
    risk_percent: float = 1.0
    min_confidence: float = 55.0
    max_risk_level: str = "MEDIUM"
    one_position_per_symbol: bool = True

    @classmethod
    def from_env(cls) -> "AutoExecutionConfig":
        risk_percent = float(os.getenv("ATLAS_AUTO_RISK_PERCENT", "1.0"))
        return cls(
            enabled=os.getenv("ATLAS_AUTO_EXECUTION_ENABLED", "false").lower() == "true",
            risk_percent=min(max(risk_percent, 0.01), 2.0),
            min_confidence=float(os.getenv("ATLAS_AUTO_MIN_CONFIDENCE", "55")),
            max_risk_level=os.getenv("ATLAS_AUTO_MAX_RISK_LEVEL", "MEDIUM").upper(),
            one_position_per_symbol=os.getenv(
                "ATLAS_ONE_POSITION_PER_SYMBOL", "true"
            ).lower() == "true",
        )


class AutoExecutionCoordinator:
    """Route approved ATLAS decisions through risk controls into MT5.

    This coordinator is separate from the Evolution Engine. Evolution may alter
    analytical weights/prompts, but it cannot invoke this class directly.
    """

    def __init__(
        self,
        broker: MT5Broker | None = None,
        config: AutoExecutionConfig | None = None,
    ):
        self.broker = broker or MT5Broker(MT5Config.from_env())
        self.config = config or AutoExecutionConfig.from_env()
        self.execution = AtlasExecutionService(
            broker=self.broker,
            policy=ExecutionPolicy(
                enabled=self.config.enabled and not self.broker.config.dry_run,
                min_confidence=self.config.min_confidence,
                max_risk_level=self.config.max_risk_level,
                allow_buy=True,
                allow_sell=True,
            ),
        )

    def status(self) -> dict[str, Any]:
        return {
            "auto_execution_enabled": self.config.enabled,
            "live_trading_enabled": not self.broker.config.dry_run,
            "effective_execution_enabled": self.execution.policy.enabled,
            "risk_percent": self.config.risk_percent,
            "min_confidence": self.config.min_confidence,
            "max_risk_level": self.config.max_risk_level,
            "one_position_per_symbol": self.config.one_position_per_symbol,
        }

    def execute_candidate(
        self,
        *,
        symbol: str,
        candidate: dict[str, Any],
        decision: dict[str, Any],
        account: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.config.enabled:
            return {"status": "BLOCKED", "reason": "AUTO_EXECUTION_DISABLED"}

        if self.broker.config.dry_run:
            return {"status": "BLOCKED", "reason": "LIVE_TRADING_DISABLED"}

        expected_action = "BUY" if candidate.get("direction") == "LONG" else "SELL"
        if candidate.get("direction") not in {"LONG", "SHORT"}:
            return {"status": "BLOCKED", "reason": "INVALID_CANDIDATE_DIRECTION"}
        if str(decision.get("decision", "WAIT")).upper() != expected_action:
            return {"status": "BLOCKED", "reason": "DECISION_DIRECTION_MISMATCH"}

        if self.config.one_position_per_symbol and self.broker.positions(symbol):
            return {"status": "BLOCKED", "reason": "POSITION_ALREADY_OPEN"}

        quote = self.broker.quote(symbol)
        entry = float(quote["ask"] if expected_action == "BUY" else quote["bid"])
        source_entry = float(candidate["entry"])
        stop_distance = abs(source_entry - float(candidate["stop_loss"]))
        target_distance = abs(float(candidate["take_profit"]) - source_entry)
        if stop_distance <= 0 or target_distance <= 0:
            return {"status": "BLOCKED", "reason": "INVALID_STOP_TARGET_DISTANCE"}

        if expected_action == "BUY":
            stop_loss = entry - stop_distance
            take_profit = entry + target_distance
            risk_direction = "LONG"
        else:
            stop_loss = entry + stop_distance
            take_profit = entry - target_distance
            risk_direction = "SHORT"

        balance = float(account.get("equity") or account.get("balance") or 0.0)
        risk = calculate_risk(
            direction=risk_direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_balance=balance,
            risk_percent=self.config.risk_percent,
        )
        if not risk.get("approved"):
            return {
                "status": "BLOCKED",
                "reason": "RISK_REJECTED",
                "risk": risk,
            }

        risk_amount = float(risk.get("actual_risk_amount") or 0.0)
        volume = self.broker.volume_for_risk(
            symbol,
            entry=entry,
            stop_loss=stop_loss,
            risk_amount=risk_amount,
        )

        execution_decision = {
            "decision": expected_action,
            "confidence": float(decision.get("confidence") or candidate.get("confidence") or 0.0),
            "risk_level": str(decision.get("risk_level") or "LOW").upper(),
        }

        result = self.execution.execute(
            symbol=symbol,
            decision=execution_decision,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return {
            **result,
            "risk": risk,
            "volume": volume,
            "entry": entry,
            "auto_execution": True,
        }
