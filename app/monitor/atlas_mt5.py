from __future__ import annotations

import time
from datetime import datetime, timezone

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles
from app.execution.atlas import AtlasExecutionService, ExecutionPolicy
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.intelligence.decision.engine import DecisionInput, UnifiedDecisionEngine
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate


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
    """Live/paper monitor that routes approved ATLAS decisions to MT5."""

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

    def _decision_from_components(
        self,
        technical: dict,
        structure: dict,
        signal: dict,
    ) -> dict:
        # Existing modules remain the signal source. Scores unavailable from
        # the legacy pipeline are neutral rather than fabricated.
        signal_direction = signal.get("direction")
        technical_score = {
            "LONG": 1.0,
            "SHORT": -1.0,
        }.get(signal_direction, 0.0)

        data = DecisionInput(
            technical_score=technical_score,
            macro_score=0.0,
            news_score=0.0,
            geopolitical_score=0.0,
            cross_asset_score=0.0,
            reaction_score=0.0,
            regime="TRANSITION",
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
        signal = generate_signal(technical, structure)
        trade = create_trade_candidate(signal, technical)
        decision = self._decision_from_components(technical, structure, signal)
        return {
            "symbol": symbol,
            "market": market_data,
            "technical": technical,
            "structure": structure,
            "signal": signal,
            "trade": trade,
            "decision": decision,
        }

    def cycle(self) -> list[dict]:
        timestamp = datetime.now(timezone.utc).isoformat()
        events: list[dict] = []

        for symbol in self.symbols:
            try:
                analysis = self.analyze_symbol(symbol)
                trade = analysis["trade"]
                decision = analysis["decision"]

                if trade.get("status") != "TRADE_CANDIDATE":
                    events.append({
                        "symbol": symbol,
                        "status": "NO_TRADE",
                        "reason": trade.get("reason", "No trade candidate."),
                        "decision": decision,
                    })
                    continue

                quote = self.broker.quote(symbol)
                entry = quote["ask"] if trade["direction"] == "LONG" else quote["bid"]

                # Use the live MT5 quote as the execution price while keeping
                # the strategy's calculated SL/TP structure.
                result = self.execution.execute(
                    symbol=symbol,
                    decision=decision,
                    volume=self._safe_float(trade["risk"].get("position_size")),
                    stop_loss=self._safe_float(trade["stop_loss"]),
                    take_profit=self._safe_float(trade["take_profit"]),
                )

                events.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "status": result.get("status"),
                    "entry_quote": entry,
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
