from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.strategies.router import generate_strategy_candidate


TIMEFRAME_MAP = {
    "1m": "TIMEFRAME_M1",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30",
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}


class AtlasMT5Monitor:
    """Live/paper monitor routing qualified strategy candidates through ATLAS decision and execution gates."""

    def __init__(
        self,
        symbols: list[str],
        interval: str = "5m",
        candle_limit: int = 200,
        cycle_seconds: int = 30,
    ):
        if interval not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported ATLAS interval: {interval}")

        self.symbols = symbols
        self.interval = interval
        self.candle_limit = candle_limit
        self.cycle_seconds = cycle_seconds
        self.strategy_mode = os.getenv("ATLAS_STRATEGY_MODE", "BALANCED").upper()

        config = MT5Config.from_env()
        self.broker = MT5Broker(config)
        self.execution = AtlasExecutionService(
            broker=self.broker,
            policy=ExecutionPolicy(
                enabled=not config.dry_run,
                min_confidence=55.0,
                max_risk_level="MEDIUM",
                allow_buy=True,
                allow_sell=True,
            ),
        )
        self.decision_engine = UnifiedDecisionEngine()
        self.running = False

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _decision_from_candidate(self, candidate: dict) -> dict:
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

    def analyze_symbol(self, symbol: str) -> dict:
        market_data = get_candles(symbol, self.interval, self.candle_limit)
        candles = market_data["candles"]
        technical = analyze_candles(candles)
        structure = analyze_structure(candles)
        candidate_obj = generate_strategy_candidate(
            symbol,
            technical,
            structure,
            mode=self.strategy_mode,
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

    def cycle(self) -> list[dict]:
        timestamp = datetime.now(timezone.utc).isoformat()
        events: list[dict] = []

        for symbol in self.symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                candidate = analysis["candidate"]
                decision = analysis["decision"]

                if not candidate:
                    events.append({
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "status": "NO_TRADE",
                        "reason": "No strategy setup qualified for scoring.",
                        "decision": decision,
                    })
                    continue

                if not candidate.get("qualified"):
                    events.append({
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "status": "NO_TRADE",
                        "reason": "Candidate failed confidence or risk qualification.",
                        "candidate": candidate,
                        "decision": decision,
                    })
                    continue

                risk = candidate.get("metadata", {}).get("risk", {})
                quote = self.broker.quote(symbol)
                entry = quote["ask"] if candidate["direction"] == "LONG" else quote["bid"]

                result = self.execution.execute(
                    symbol=symbol,
                    decision=decision,
                    volume=self._safe_float(risk.get("position_size")),
                    stop_loss=self._safe_float(candidate["stop_loss"]),
                    take_profit=self._safe_float(candidate["take_profit"]),
                )

                events.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "status": result.get("status"),
                    "entry_quote": entry,
                    "strategy": candidate["strategy"],
                    "classification": candidate["classification"],
                    "setup_lane": candidate["setup_lane"],
                    "confidence": candidate["confidence"],
                    "candidate": candidate,
                    "decision": decision,
                    "execution": result,
                })

            except MT5ExecutionError as exc:
                events.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "status": "MT5_ERROR",
                    "error": str(exc),
                })
            except Exception as exc:
                events.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "status": "ERROR",
                    "error": str(exc),
                })

        return events

    def run_forever(self) -> None:
        self.running = True
        account = self.broker.connect()
        print("ATLAS MT5 monitor started")
        print(f"MODE: {'LIVE' if not self.broker.config.dry_run else 'DRY RUN'}")
        print(f"STRATEGY MODE: {self.strategy_mode}")
        print(f"ACCOUNT: {account['login']} / {account['server']}")
        print(f"SYMBOLS: {self.symbols}")
        print(f"TIMEFRAME: {self.interval}")

        try:
            while self.running:
                for event in self.cycle():
                    print(event)
                time.sleep(self.cycle_seconds)
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.broker.disconnect()

    def stop(self) -> None:
        self.running = False
