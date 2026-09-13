from __future__ import annotations

import math
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.heartbeat import AtlasHeartbeat
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, mt5
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.intelligence.journal import SignalJournal
from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError
from app.risk.ledger_metrics import calculate_ledger_risk_state
from app.risk.manager import calculate_risk
from app.strategies.router import generate_strategy_candidate
from app.strategy.universe import build_universe


TIMEFRAME_MAP = {
    "1m": "TIMEFRAME_M1",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30",
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}

TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class AtlasMT5Monitor:
    """Forward-demo monitor that never submits an MT5 order.

    Qualified candidates are opened in a persistent paper ledger, then closed
    only when a later MT5 quote reaches their stop loss or take profit. Every
    open/close/error is journaled locally and published to Supabase whenever
    the worker has server-side Supabase credentials.
    """

    def __init__(
        self,
        symbols: list[str] | None = None,
        interval: str = "5m",
        candle_limit: int = 200,
        cycle_seconds: int = 30,
        top_n: int = 30,
    ):
        if interval not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported ATLAS interval: {interval}")

        config = MT5Config.from_env()
        if not config.dry_run:
            raise ValueError(
                "ATLAS demo monitor refuses to start while ATLAS_LIVE_TRADING=true. "
                "Set it to false for paper validation."
            )

        self.symbols = symbols or []
        self.interval = interval
        self.candle_limit = candle_limit
        self.cycle_seconds = max(10, int(cycle_seconds))
        self.top_n = max(1, int(top_n))
        self.strategy_mode = os.getenv("ATLAS_STRATEGY_MODE", "BALANCED").upper()
        self.auto_discover = os.getenv("ATLAS_AUTO_DISCOVER_SYMBOLS", "true").lower() == "true"
        self.preferred_canonical = {
            item.strip().upper()
            for item in os.getenv(
                "ATLAS_PREFERRED_CANONICAL",
                "XAUUSD,XAGUSD,NGAS,EURUSD,XRPUSDT,SOLUSDT",
            ).split(",")
            if item.strip()
        }
        self.persist_all_signals = os.getenv("ATLAS_PERSIST_ALL_SIGNALS", "false").lower() == "true"
        self.reentry_cooldown_seconds = max(
            TIMEFRAME_SECONDS[interval],
            int(os.getenv("ATLAS_REENTRY_COOLDOWN_SECONDS", str(TIMEFRAME_SECONDS[interval]))),
        )

        self.broker = MT5Broker(config)
        # Retained as an explicit invariant for code paths that inspect
        # execution status. The demo monitor never calls this service.
        self.execution = AtlasExecutionService(
            broker=self.broker,
            policy=ExecutionPolicy(enabled=False),
        )
        self.decision_engine = UnifiedDecisionEngine()
        self.ledger = MT5PaperLedger()
        self.journal = SignalJournal()
        self.heartbeat = AtlasHeartbeat(self.broker)
        self.running = False
        self.universe: list[dict[str, Any]] = []
        self.account_equity = float(os.getenv("ATLAS_DEMO_ACCOUNT_EQUITY", "10000"))

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _record_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Write a local audit record and optionally publish its safe envelope."""
        payload = self.journal.append(event)
        status = str(event.get("status", "DRY_RUN"))
        is_material = status not in {"NO_TRADE", "SKIPPED"}

        if is_material or self.persist_all_signals:
            decision = event.get("decision") or {}
            if not isinstance(decision, dict):
                decision = {}
            self.heartbeat.publish_event(
                {
                    "symbol": str(event.get("symbol", "ATLAS")),
                    "timeframe": str(event.get("timeframe", self.interval)),
                    "decision": str(decision.get("decision", "WAIT")).upper(),
                    "confidence": decision.get("confidence", event.get("confidence")),
                    "risk_level": decision.get("risk_level"),
                    "directional_score": decision.get("directional_score"),
                    "status": status,
                    "reason": str(event.get("reason", ""))[:500],
                    "payload": payload,
                }
            )
        return payload

    def discover_symbols(self) -> list[str]:
        if not self.auto_discover and self.symbols:
            return self.symbols

        ranked = build_universe(self.broker.symbols(), top_n=self.top_n)
        preferred = [
            item
            for item in ranked
            if item.canonical_symbol in self.preferred_canonical and item.tradeable
        ]
        selected = preferred or ranked
        self.universe = [item.to_dict() for item in selected]
        discovered = [item.broker_symbol for item in selected if item.tradeable]
        if discovered:
            self.symbols = discovered
        return self.symbols

    def _decision_from_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        direction = candidate.get("direction")
        technical_score = {"LONG": 1.0, "SHORT": -1.0}.get(direction, 0.0)
        data = DecisionInput(
            technical_score=technical_score,
            macro_score=0.0,
            news_score=0.0,
            geopolitical_score=0.0,
            cross_asset_score=0.0,
            reaction_score=0.0,
            regime=candidate.get("regime", "TRANSITION"),
            conflict_score=0.0,
            volatility_score=0.0,
            event_risk_score=0.0,
        )
        return self.decision_engine.analyze(data)

    def analyze_symbol(self, symbol: str) -> dict[str, Any]:
        if mt5 is None:
            raise MT5ExecutionError("MT5 candles require the Windows worker.")
        candles = self.broker.candles(
            symbol, getattr(mt5, TIMEFRAME_MAP[self.interval]), self.candle_limit
        )
        if len(candles) < 50:
            raise MT5ExecutionError(f"{symbol}: at least 50 candles are required.")
        market_data = {
            "symbol": symbol, "interval": self.interval, "source": "MT5",
            "count": len(candles), "candles": candles,
        }
        technical = analyze_candles(candles)
        structure = analyze_structure(candles)
        candidate_obj = generate_strategy_candidate(
            symbol,
            technical,
            structure,
            mode=self.strategy_mode,
            account_balance=self.account_equity,
        )
        candidate = candidate_obj.to_dict() if candidate_obj else None
        decision = self._decision_from_candidate(candidate or {})
        return {
            "symbol": symbol,
            "market": market_data,
            "technical": technical,
            "structure": structure,
            "candidate": candidate,
            "decision": decision,
        }

    @staticmethod
    def _rebase_levels(candidate: dict[str, Any], entry: float) -> tuple[float, float]:
        source_entry = float(candidate["entry"])
        stop_distance = abs(source_entry - float(candidate["stop_loss"]))
        target_distance = abs(float(candidate["take_profit"]) - source_entry)
        if stop_distance <= 0 or target_distance <= 0:
            raise PaperLedgerError("Candidate has invalid stop/target distances.")

        if candidate["direction"] == "LONG":
            return entry - stop_distance, entry + target_distance
        return entry + stop_distance, entry - target_distance

    def _close_due_positions(self, timestamp: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        symbols = {str(position["symbol"]) for position in self.ledger.open_positions()}
        for symbol in symbols:
            try:
                quote = self.broker.quote(symbol)
                for trade in self.ledger.close_due_positions(
                    symbol,
                    bid=float(quote["bid"]),
                    ask=float(quote["ask"]),
                ):
                    event = {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": trade["timeframe"],
                        "status": "PAPER_TRADE_CLOSED",
                        "reason": trade["exit_reason"],
                        "decision": trade["decision"],
                        "confidence": trade["confidence"],
                        "trade": trade,
                    }
                    self._record_event(event)
                    events.append(event)
            except (MT5ExecutionError, PaperLedgerError) as exc:
                event = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "MT5_ERROR",
                    "reason": str(exc),
                    "decision": {"decision": "WAIT"},
                }
                self._record_event(event)
                events.append(event)
        return events

    def _open_paper_trade(
        self,
        *,
        timestamp: str,
        symbol: str,
        candidate: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        last_closed = self.ledger.last_closed_trade(symbol)
        if last_closed:
            closed_at = datetime.fromisoformat(str(last_closed["closed_at"]))
            elapsed = (datetime.now(timezone.utc) - closed_at).total_seconds()
            cooldown_remaining = self.reentry_cooldown_seconds - elapsed
            if cooldown_remaining > 0:
                remaining = math.ceil(cooldown_remaining)
                return {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "SKIPPED",
                    "reason": (
                        "Re-entry cooldown is active after the last paper close "
                        f"({remaining}s remaining)."
                    ),
                    "candidate": candidate,
                    "decision": decision,
                }

        expected_action = "BUY" if candidate["direction"] == "LONG" else "SELL"
        if decision.get("decision") != expected_action:
            return {
                "timestamp": timestamp,
                "symbol": symbol,
                "timeframe": self.interval,
                "status": "NO_TRADE",
                "reason": "Unified decision gate did not confirm the strategy direction.",
                "candidate": candidate,
                "decision": decision,
            }

        if self.ledger.has_open_position(symbol):
            return {
                "timestamp": timestamp,
                "symbol": symbol,
                "timeframe": self.interval,
                "status": "SKIPPED",
                "reason": "A demo position is already open for this symbol.",
                "candidate": candidate,
                "decision": decision,
            }

        quote = self.broker.quote(symbol)
        entry = float(quote["ask"] if candidate["direction"] == "LONG" else quote["bid"])
        stop_loss, take_profit = self._rebase_levels(candidate, entry)
        base_risk = candidate.get("metadata", {}).get("risk", {})
        ledger_risk = calculate_ledger_risk_state(self.ledger, self.account_equity)
        risk = calculate_risk(
            direction=candidate["direction"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_balance=self.account_equity,
            risk_percent=self._safe_float(base_risk.get("risk_percent"), 0.5),
            daily_realized_pnl=ledger_risk["daily_realized_pnl"],
            open_risk_percent=ledger_risk["open_risk_percent"],
        )
        if not risk.get("approved", False):
            return {
                "timestamp": timestamp,
                "symbol": symbol,
                "timeframe": self.interval,
                "status": "NO_TRADE",
                "reason": str(risk.get("reason", "Risk gate rejected the paper trade.")),
                "candidate": candidate,
                "decision": decision,
                "risk": risk,
            }

        trade = self.ledger.open_trade(
            symbol=symbol,
            direction=candidate["direction"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=self._safe_float(risk.get("position_size")),
            risk=risk,
            strategy=str(candidate["strategy"]),
            confidence=self._safe_float(candidate["confidence"]),
            timeframe=self.interval,
            decision=decision,
        )
        return {
            "timestamp": timestamp,
            "symbol": symbol,
            "timeframe": self.interval,
            "status": "PAPER_TRADE_OPENED",
            "reason": "Qualified strategy, decision, and risk gates approved a paper entry.",
            "candidate": candidate,
            "decision": decision,
            "trade": trade,
        }

    def cycle(self) -> list[dict[str, Any]]:
        timestamp = datetime.now(timezone.utc).isoformat()
        events = self._close_due_positions(timestamp)
        if self.auto_discover:
            self.discover_symbols()

        for symbol in self.symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                candidate = analysis["candidate"]
                decision = analysis["decision"]
                if not candidate:
                    event = {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": self.interval,
                        "status": "NO_TRADE",
                        "reason": "No strategy setup qualified for scoring.",
                        "decision": decision,
                    }
                elif not candidate.get("qualified"):
                    event = {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": self.interval,
                        "status": "NO_TRADE",
                        "reason": "Candidate failed confidence or risk qualification.",
                        "candidate": candidate,
                        "decision": decision,
                    }
                else:
                    event = self._open_paper_trade(
                        timestamp=timestamp,
                        symbol=symbol,
                        candidate=candidate,
                        decision=decision,
                    )
                self._record_event(event)
                events.append(event)
            except (MT5ExecutionError, PaperLedgerError) as exc:
                event = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "MT5_ERROR",
                    "reason": str(exc),
                    "decision": {"decision": "WAIT"},
                }
                self._record_event(event)
                events.append(event)
            except Exception as exc:
                event = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "ERROR",
                    "reason": str(exc),
                    "decision": {"decision": "WAIT"},
                }
                self._record_event(event)
                events.append(event)
        return events

    def run_once(self) -> list[dict[str, Any]]:
        """Run one connected demo cycle and return its audit events."""
        try:
            account = self.broker.connect()
            self.account_equity = float(account["equity"])
            self.heartbeat.publish_connection(account, "connected")
            self.discover_symbols()
            return self.cycle()
        finally:
            self.broker.disconnect()

    def run_forever(self) -> None:
        """Reconnect each cycle; transient MT5 failures never discard the ledger."""
        self.running = True
        print("ATLAS forward-demo: PAPER ONLY; no MT5 orders", flush=True)
        try:
            while self.running:
                try:
                    for event in self.run_once():
                        print(event, flush=True)
                except MT5ExecutionError as exc:
                    self.heartbeat.publish_connection({}, "error")
                    event = self._record_event({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "symbol": "ATLAS", "timeframe": self.interval,
                        "status": "MT5_ERROR", "reason": str(exc),
                        "decision": {"decision": "WAIT"},
                    })
                    print(event, flush=True)
                if self.running:
                    time.sleep(self.cycle_seconds)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.broker.disconnect()

    def stop(self) -> None:
        self.running = False
