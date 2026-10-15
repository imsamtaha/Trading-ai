from __future__ import annotations

import os
import math
import time
from dataclasses import dataclass
from typing import Any

from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.risk.manager import calculate_risk
from app.execution.portfolio_lock import portfolio_lock, ExecutionBusy
from app.intelligence.specialists import RiskExecutive
from app.risk.correlation import measure_correlations
from app.risk.multi_asset import MultiAssetRiskEngine


@dataclass(frozen=True)
class AutoExecutionConfig:
    enabled: bool = False
    risk_percent: float = 1.0
    min_confidence: float = 55.0
    max_risk_level: str = "MEDIUM"
    one_position_per_symbol: bool = True
    max_entry_drift_points: float = 20.0
    max_candidate_age_seconds: float = 60.0
    max_quote_age_seconds: float = 30.0
    max_abs_correlation: float | None = None

    def __post_init__(self):
        for name in ("risk_percent", "min_confidence", "max_entry_drift_points",
                     "max_candidate_age_seconds", "max_quote_age_seconds"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.risk_percent > 2 or self.min_confidence > 100:
            raise ValueError("Risk/confidence configuration exceeds its allowed range.")
        if self.max_risk_level not in AtlasExecutionService.RISK_ORDER:
            raise ValueError("Unknown maximum risk level.")
        if self.max_abs_correlation is not None and (not math.isfinite(self.max_abs_correlation) or not 0 < self.max_abs_correlation <= 1):
            raise ValueError("Correlation limit must be finite and between 0 and 1.")

    @classmethod
    def from_env(cls) -> "AutoExecutionConfig":
        risk_percent = float(os.getenv("ATLAS_AUTO_RISK_PERCENT", "1.0"))
        return cls(
            enabled=os.getenv("ATLAS_AUTO_EXECUTION_ENABLED", "false").lower() == "true",
            risk_percent=risk_percent,
            max_abs_correlation=float(os.environ["ATLAS_MAX_ABS_CORRELATION"]) if os.getenv("ATLAS_MAX_ABS_CORRELATION") else None,
            max_entry_drift_points=float(os.getenv("ATLAS_AUTO_MAX_ENTRY_DRIFT_POINTS", "20")),
            max_candidate_age_seconds=float(os.getenv("ATLAS_AUTO_MAX_CANDIDATE_AGE_SECONDS", "60")),
            max_quote_age_seconds=float(os.getenv("ATLAS_MT5_MAX_QUOTE_AGE_SECONDS", "30")),
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

        try:
            with portfolio_lock():
                return self._execute_locked(symbol=symbol, candidate=candidate, decision=decision, account=account,
                                            expected_action=expected_action)
        except (ExecutionBusy, OSError):
            return {"status": "BLOCKED", "reason": "EXECUTION_BUSY"}

    def _execute_locked(self, *, symbol, candidate, decision, account, expected_action):
        try:
            if self.config.one_position_per_symbol and self.broker.positions(symbol):
                return {"status": "BLOCKED", "reason": "POSITION_ALREADY_OPEN"}
            if candidate.get("qualified") is not True:
                return {"status": "BLOCKED", "reason": "CANDIDATE_NOT_QUALIFIED"}
            if candidate.get("symbol", symbol) != symbol:
                return {"status": "BLOCKED", "reason": "CANDIDATE_SYMBOL_MISMATCH"}
            created = float(candidate["created_at"])
            age = time.time() - created
            if not math.isfinite(created) or age < -5 or age > self.config.max_candidate_age_seconds:
                return {"status": "BLOCKED", "reason": "CANDIDATE_STALE"}
            strategy_risk = candidate["metadata"]["risk"]
            requested_risk = float(strategy_risk["risk_percent"])
            if strategy_risk.get("approved") is not True or not math.isfinite(requested_risk) or not 0 < requested_risk <= 2:
                return {"status": "BLOCKED", "reason": "INVALID_STRATEGY_RISK_BUDGET"}
            risk_percent = min(self.config.risk_percent, requested_risk)
            source_entry = float(candidate["entry"])
            stop_loss = float(candidate["stop_loss"])
            take_profit = float(candidate["take_profit"])
            confidence = float(decision["confidence"])
            if not all(math.isfinite(v) and v > 0 for v in (source_entry, stop_loss, take_profit, confidence)):
                return {"status": "BLOCKED", "reason": "INVALID_CANDIDATE_VALUES"}
            if not (stop_loss < source_entry < take_profit if expected_action == "BUY"
                    else take_profit < source_entry < stop_loss):
                return {"status": "BLOCKED", "reason": "INVALID_STOP_TARGET_DISTANCE"}
            quote = self.broker.quote(symbol)
            quote_time = float(quote.get("time_msc", 0)) / 1000 or float(quote.get("time", 0))
            quote_age = time.time() - quote_time
            if not math.isfinite(quote_time) or quote_age < -5 or quote_age > self.config.max_quote_age_seconds:
                return {"status": "BLOCKED", "reason": "QUOTE_STALE"}
            entry = float(quote["ask"] if expected_action == "BUY" else quote["bid"])
            point = float(quote["point"])
            if not math.isfinite(entry) or entry <= 0 or not math.isfinite(point) or point <= 0:
                return {"status": "BLOCKED", "reason": "INVALID_QUOTE"}
            allowed_drift = point * self.config.max_entry_drift_points
            if abs(entry - source_entry) > allowed_drift + 1e-12:
                return {"status": "BLOCKED", "reason": "ENTRY_DRIFT"}
            # Retain the qualified strategy levels. Recheck reward/risk at the current quote.
            portfolio = self.broker.risk_snapshot()
            if self.config.one_position_per_symbol and any(
                position.get("symbol") == symbol for position in portfolio.get("positions", [])
            ):
                return {"status": "BLOCKED", "reason": "POSITION_ALREADY_OPEN"}
            expected_account = MT5Broker.account_identity(account)
            if MT5Broker.account_identity(portfolio) != expected_account:
                return {"status": "BLOCKED", "reason": "ACCOUNT_CHANGED"}
            snapshot_age = time.time() - float(portfolio["timestamp"])
            if not math.isfinite(snapshot_age) or snapshot_age < -5 or snapshot_age > self.config.max_quote_age_seconds:
                return {"status": "BLOCKED", "reason": "PORTFOLIO_STALE"}
            risk = calculate_risk(
                direction=candidate["direction"], entry=entry, stop_loss=stop_loss,
                take_profit=take_profit, account_balance=float(portfolio["equity"]),
                risk_percent=risk_percent, daily_realized_pnl=float(portfolio["daily_realized_pnl"]),
                open_risk_percent=float(portfolio["open_risk_percent"]),
                daily_start_capital=float(portfolio["daily_start_capital"]),
            )
            if not risk.get("approved"):
                return {"status": "BLOCKED", "reason": "RISK_REJECTED", "risk": risk}
            snapshot_id = f"{symbol}:{portfolio['timestamp']}"
            open_symbols = tuple(str(p['symbol']) for p in portfolio.get('positions', []))
            correlation = None
            if open_symbols and self.config.max_abs_correlation is not None:
                from app.execution.mt5 import mt5
                try:
                    histories = {key: self.broker.candles(key, mt5.TIMEFRAME_M5, 200) for key in {symbol, *open_symbols}}
                    from datetime import datetime, timezone
                    correlation = measure_correlations(symbol, open_symbols, histories,
                        limit=self.config.max_abs_correlation, snapshot_id=snapshot_id,
                        as_of=datetime.fromtimestamp(float(portfolio['timestamp']), timezone.utc).isoformat())
                except (MT5ExecutionError, ValueError, KeyError, TypeError, AttributeError):
                    pass
            risk_amount = float(risk["actual_risk_amount"])
            position = MultiAssetRiskEngine(float(portfolio['equity']),risk_percent / 100,broker=self.broker).calculate_position(
                symbol,entry,stop_loss,portfolio['free_margin'],used_margin=portfolio['used_margin'],
                direction=expected_action,max_cash_risk=risk_amount,entry_includes_spread=True,
                spread_price=float(quote['ask'])-float(quote['bid']))
            verdict = RiskExecutive().assess(risk, symbol=symbol, snapshot_id=snapshot_id,
                                             open_symbols=open_symbols, correlation=correlation, position=position)
            if verdict['allowed'] is not True:
                return {"status": "BLOCKED", "reason": "RISK_EXECUTIVE_VETO", "risk": risk, "risk_executive": verdict}
            execution_decision = {**decision, 'symbol': symbol, 'snapshot_id': snapshot_id,
                                  'specialist_schema_version': 1, 'risk_executive': verdict}
            volume = float(position['lots'])
            result = self.execution.execute(
                symbol=symbol, decision=execution_decision, volume=volume, stop_loss=stop_loss,
                take_profit=take_profit, max_cash_risk=risk_amount,
                expected_entry=source_entry, max_entry_deviation=allowed_drift,
                expected_account=expected_account,
                one_position_per_symbol=self.config.one_position_per_symbol,
                expected_position_fingerprint=portfolio['position_fingerprint'],
            )
            return {**result, "risk": risk, "position_sizing":position, "risk_executive":verdict,
                    "volume": volume, "entry": entry, "auto_execution": True}
        except (MT5ExecutionError, ValueError, TypeError, KeyError) as exc:
            return {"status": "BLOCKED", "reason": "EXECUTION_INPUT_UNAVAILABLE", "detail": str(exc)}
