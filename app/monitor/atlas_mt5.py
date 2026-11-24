from __future__ import annotations

import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.heartbeat import AtlasHeartbeat
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, mt5
from app.intelligence.shadow_selector import ShadowSelector
from app.intelligence.confidence import SignalQualityEngine
from app.intelligence.council_adapters import build_paper_council, record_settled_paper_outcome
from app.intelligence.council_training import AtlasCouncilTrainer, CouncilTrainingJournal, save_profile
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.intelligence.journal import SignalJournal
from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError
from app.risk.ledger_metrics import calculate_ledger_risk_state
from app.risk.manager import calculate_risk
from app.strategies.router import generate_strategy_candidate
from app.strategy.universe import build_universe, diversify_universe, normalize_symbol, classify_symbol


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
                "XAUUSD,XAGUSD,XPTUSD,NGAS,WTI,EURUSD,GBPUSD,USDJPY,AUDJPY,NAS100,US500,GER40,JP225,BTCUSD,ETHUSD,SOLUSDT,XRPUSDT,ADAUSD,WHEAT,CORN",
            ).split(",")
            if item.strip()
        }
        self.persist_all_signals = os.getenv("ATLAS_PERSIST_ALL_SIGNALS", "false").lower() == "true"
        self.max_quote_age_seconds = max(
            1,
            int(os.getenv("ATLAS_MT5_MAX_QUOTE_AGE_SECONDS", "30")),
        )
        self.quote_time_offset_seconds = int(
            os.getenv("ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS", "0")
        )
        if abs(self.quote_time_offset_seconds) > 14 * 3600:
            raise ValueError("ATLAS MT5 quote time offset must be within +/-14 hours.")
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
        self.council_training_enabled = (
            os.getenv("ATLAS_COUNCIL_TRAINING_ENABLED", "false").lower() == "true"
        )
        self.council_training_journal = CouncilTrainingJournal(
            os.getenv("ATLAS_COUNCIL_TRAINING_JOURNAL", "data/atlas_council_training.jsonl")
        )
        self.council_profile_path = Path(
            os.getenv("ATLAS_COUNCIL_PROFILE", "data/atlas_council_profile.json")
        )
        self.council_minimum_samples = max(
            1, int(os.getenv("ATLAS_COUNCIL_MINIMUM_SAMPLES", "5"))
        )
        self.shadow_enabled = os.getenv("ATLAS_SHADOW_TRAINING_ENABLED", "false").lower() == "true"
        self.shadow_selector = ShadowSelector()
        self.shadow_report_path = Path(os.getenv("ATLAS_SHADOW_REPORT", "data/atlas_shadow_report.json"))
        self.shadow_journal_path = Path(os.getenv("ATLAS_SHADOW_JOURNAL", "data/atlas_shadow_predictions.jsonl"))
        self.shadow_closed_count = -1
        self.cycle_rotation = 0
        self.accelerator_enabled = os.getenv("ATLAS_TRAINING_ACCELERATOR_ENABLED", "false").lower() == "true"
        self.accelerator_node = os.getenv("ATLAS_NODE_EXE", "node")
        self.category_position_limit = max(0, int(os.getenv("ATLAS_CATEGORY_POSITION_LIMIT", "0")))
        self.signal_quality_engine = SignalQualityEngine()
        self.council_profile = self._load_council_profile()

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _load_council_profile(self) -> dict[str, Any] | None:
        if not self.council_profile_path.exists():
            return None
        try:
            payload = json.loads(self.council_profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if str(payload.get("training_environment", "")).upper() != "PAPER":
            return None
        if bool(payload.get("broker_execution_allowed", True)):
            return None
        return payload

    def _refresh_council_profile(self) -> dict[str, Any] | None:
        if not self.council_training_enabled:
            return self.council_profile
        examples = self.council_training_journal.load()
        profile = AtlasCouncilTrainer(
            minimum_samples=self.council_minimum_samples
        ).fit(examples)
        save_profile(profile, str(self.council_profile_path))
        self.council_profile = profile
        return profile

    def _build_council_gate(
        self,
        *,
        timestamp: str,
        symbol: str,
        candidate: dict[str, Any],
        decision: dict[str, Any],
        risk: dict[str, Any],
    ) -> dict[str, Any]:
        expected_action = "BUY" if candidate["direction"] == "LONG" else "SELL"
        quality = self.signal_quality_engine.evaluate(
            decision,
            mtf_alignment="ALIGNED"
            if str(decision.get("decision", "")).upper() == expected_action
            else "MIXED",
        )
        reasons = [
            f"strategy={candidate.get('strategy', 'UNKNOWN')}",
            f"regime={candidate.get('regime', 'UNKNOWN')}",
            f"unified_decision={decision.get('decision', 'WAIT')}",
        ]
        signal = {
            "direction": candidate["direction"],
            "confidence": self._safe_float(candidate.get("confidence")),
            "reasons": reasons,
        }
        snapshot_id = f"{symbol.upper()}:{self.interval}:{timestamp}"
        return build_paper_council(
            symbol=symbol,
            snapshot_id=snapshot_id,
            signal=signal,
            risk=risk,
            data_quality=1.0,
            quality=quality,
            agent_profile=self.council_profile,
        )

    def _record_council_training_outcome(self, trade: dict[str, Any]) -> dict[str, Any] | None:
        if not self.council_training_enabled:
            return None
        context = trade.get("training_context")
        if not isinstance(context, dict):
            return None
        council = context.get("council")
        trade_intent = context.get("trade_intent")
        if not isinstance(council, dict) or not isinstance(trade_intent, dict):
            return None

        direction = "BUY" if str(trade.get("direction", "")).upper() == "LONG" else "SELL"
        r_multiple = self._safe_float(trade.get("r_multiple"))
        if r_multiple > 0:
            realized_direction = direction
        elif r_multiple < 0:
            realized_direction = "SELL" if direction == "BUY" else "BUY"
        else:
            realized_direction = "HOLD"

        record = record_settled_paper_outcome(
            council=council,
            trade_intent=trade_intent,
            realized_direction=realized_direction,
            journal=self.council_training_journal,
        )
        profile = self._refresh_council_profile() or {}
        return {
            "snapshot_id": record.get("snapshot_id"),
            "realized_direction": realized_direction,
            "total_examples": profile.get("total_examples", 0),
            "minimum_samples": profile.get(
                "minimum_samples", self.council_minimum_samples
            ),
        }

    def _validate_quote_freshness(self, quote: dict[str, Any]) -> tuple[bool, str]:
        """Fail closed when an MT5 quote has no trustworthy current timestamp."""
        try:
            time_msc = int(quote.get("time_msc", 0) or 0)
            if time_msc:
                quote_timestamp = time_msc / 1000.0
            else:
                quote_timestamp = float(int(quote.get("time", 0) or 0))
        except (TypeError, ValueError, OverflowError):
            return False, "MT5 quote timestamp is invalid."

        if quote_timestamp < 0:
            return False, "MT5 quote timestamp is invalid."
        if quote_timestamp == 0:
            return False, "MT5 quote timestamp is missing."

        quote_timestamp -= self.quote_time_offset_seconds
        age_seconds = datetime.now(timezone.utc).timestamp() - quote_timestamp

        if age_seconds < -5:
            return False, "MT5 quote timestamp is unexpectedly in the future."

        if age_seconds > self.max_quote_age_seconds:
            return (
                False,
                f"MT5 quote is stale ({age_seconds:.1f}s old; "
                f"maximum {self.max_quote_age_seconds}s).",
            )

        return True, ""

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

        raw = self.broker.symbols()
        ranked = build_universe(raw, top_n=max(self.top_n, len(raw)))
        # Preferences prioritize within each category rather than removing categories.
        ranked.sort(key=lambda item: (item.canonical_symbol not in self.preferred_canonical,
                                     -item.opportunity_score, item.priority, item.canonical_symbol))
        selected = diversify_universe(ranked, top_n=self.top_n)
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
                quote_fresh, quote_reason = self._validate_quote_freshness(quote)
                if not quote_fresh:
                    raise MT5ExecutionError(quote_reason)
                for trade in self.ledger.close_due_positions(
                    symbol,
                    bid=float(quote["bid"]),
                    ask=float(quote["ask"]),
                ):
                    training = None
                    try:
                        training = self._record_council_training_outcome(trade)
                    except (OSError, TypeError, ValueError) as exc:
                        training = {
                            "status": "ERROR",
                            "reason": f"Council training record rejected: {exc}",
                        }
                    event = {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "timeframe": trade["timeframe"],
                        "status": "PAPER_TRADE_CLOSED",
                        "reason": trade["exit_reason"],
                        "decision": trade["decision"],
                        "confidence": trade["confidence"],
                        "trade": trade,
                        "training": training,
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

        category = (classify_symbol(normalize_symbol(symbol)) or ("UNKNOWN", 3))[0]
        if self.category_position_limit and category in {"CRYPTO", "STOCKS"}:
            same_category = sum(
                (classify_symbol(normalize_symbol(str(p["symbol"]))) or ("UNKNOWN", 3))[0] == category
                for p in self.ledger.open_positions()
            )
            if same_category >= self.category_position_limit:
                return {"timestamp": timestamp, "symbol": symbol, "timeframe": self.interval,
                        "status": "NO_TRADE", "reason": f"{category} concentration limit reached.",
                        "candidate": candidate, "decision": decision}

        quote = self.broker.quote(symbol)
        quote_fresh, quote_reason = self._validate_quote_freshness(quote)
        if not quote_fresh:
            return {
                "timestamp": timestamp,
                "symbol": symbol,
                "timeframe": self.interval,
                "status": "NO_TRADE",
                "reason": quote_reason,
                "candidate": candidate,
                "decision": decision,
            }

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
        if risk.get("approved") is not True:
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

        training_context = None
        if self.council_training_enabled:
            try:
                training_context = self._build_council_gate(
                    timestamp=timestamp,
                    symbol=symbol,
                    candidate=candidate,
                    decision=decision,
                    risk=risk,
                )
            except (TypeError, ValueError) as exc:
                return {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "NO_TRADE",
                    "reason": f"ATLAS Council gate rejected malformed evidence: {exc}",
                    "candidate": candidate,
                    "decision": decision,
                    "risk": risk,
                }

            trade_intent = training_context["trade_intent"]
            if str(trade_intent.get("decision", "")).upper() != expected_action:
                return {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "timeframe": self.interval,
                    "status": "NO_TRADE",
                    "reason": "ATLAS Council/Executive did not confirm the Paper direction.",
                    "candidate": candidate,
                    "decision": decision,
                    "risk": risk,
                    "council": training_context["council"],
                    "trade_intent": trade_intent,
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
            training_context=training_context,
        )
        return {
            "timestamp": timestamp,
            "symbol": symbol,
            "timeframe": self.interval,
            "status": "PAPER_TRADE_OPENED",
            "reason": (
                "Strategy, deterministic decision, Senior Risk, and ATLAS Council "
                "approved a Paper entry."
                if self.council_training_enabled
                else "Qualified strategy, decision, and risk gates approved a paper entry."
            ),
            "candidate": candidate,
            "decision": decision,
            "council": training_context["council"] if training_context else None,
            "trade_intent": training_context["trade_intent"] if training_context else None,
            "trade": trade,
        }

    def _refresh_shadow_training(self) -> None:
        if not self.shadow_enabled:
            return
        try:
            closed = self.ledger.closed_trades()
            if len(closed) != self.shadow_closed_count:
                self.shadow_selector.fit(closed)
                self.shadow_selector.save_report(self.shadow_report_path)
                self.shadow_closed_count = len(closed)
                if self.accelerator_enabled:
                    root = Path(__file__).resolve().parents[2]
                    try:
                        result = subprocess.run(
                            [self.accelerator_node, str(root / "scripts/atlas_training_accelerator.mjs"),
                             "--journal", str(self.council_training_journal.path.resolve()),
                             "--ledger", str(self.ledger.path.resolve()),
                             "--output-dir", str(root / ".runtime/research/training-accelerator")],
                            cwd=root, capture_output=True, text=True, timeout=15,
                        )
                        if result.returncode:
                            print(f"Agent accelerator deferred: {result.stderr[:300]}", flush=True)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        print(f"Agent accelerator unavailable: {exc}", flush=True)
        except (OSError, TypeError, ValueError) as exc:
            print(f"Shadow training unavailable: {exc}", flush=True)

    def _record_shadow_prediction(self, timestamp, symbol, candidate):
        if not self.shadow_enabled or not candidate:
            return
        try:
            record = {"timestamp": timestamp, "symbol": symbol,
                      "direction": candidate["direction"], "strategy": candidate["strategy"],
                      "confidence": candidate["confidence"],
                      "qualified": bool(candidate.get("qualified")),
                      "opened_at": timestamp}
            record["prediction_id"] = f"{timestamp}:{symbol}"
            prediction = self.shadow_selector.predict(record)
            self.shadow_journal_path.parent.mkdir(parents=True, exist_ok=True)
            with self.shadow_journal_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({**record, "shadow": prediction}, allow_nan=False)+"\n")
            return {**prediction, "prediction_id": record["prediction_id"]}
        except (OSError, TypeError, ValueError, KeyError) as exc:
            print(f"Shadow prediction unavailable: {exc}", flush=True)

    def cycle(self) -> list[dict[str, Any]]:
        timestamp = datetime.now(timezone.utc).isoformat()
        events = self._close_due_positions(timestamp)
        self._refresh_shadow_training()
        if self.auto_discover:
            self.discover_symbols()

        offset = self.cycle_rotation % max(1, len(self.symbols))
        ordered_symbols = self.symbols[offset:] + self.symbols[:offset]
        self.cycle_rotation += 1
        for symbol in ordered_symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                candidate = analysis["candidate"]
                decision = analysis["decision"]
                shadow = self._record_shadow_prediction(timestamp, symbol, candidate)
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
                if shadow:
                    event["shadow"] = shadow
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
