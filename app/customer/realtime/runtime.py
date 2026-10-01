from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timezone

from app.analysis.technical import analyze_candles
from app.customer.contracts import CustomerContext, Mode
from app.customer.execution.demo_adapter import DemoAdapter
from app.customer.realtime.cycle import CustomerRealtimeCycle
from app.customer.realtime.snapshot import build_snapshot
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, mt5


class MT5DemoRuntime:
    def __init__(self, broker_factory=None):
        self.broker_factory = broker_factory or self._default_broker

    @staticmethod
    def _default_broker():
        # LIVE_DEMO must send orders only to an MT5 demo account.
        return MT5Broker(replace(MT5Config.from_env(), dry_run=False))

    @staticmethod
    def _timeframe(value: str) -> int:
        if mt5 is None:
            raise MT5ExecutionError("MetaTrader5 package is unavailable.")
        mapping = {
            "5m": mt5.TIMEFRAME_M5, "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30, "1h": mt5.TIMEFRAME_H1,
        }
        if value not in mapping:
            raise ValueError("Unsupported demo timeframe")
        return mapping[value]

    def run(self, *, customer_id: str, account_id: str, symbol: str, timeframe: str, demo_volume: float, requested_risk_pct: float, learned_weights: dict[str, float] | None = None) -> dict:
        broker = self.broker_factory()
        try:
            account = broker.connect()
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0) if mt5 is not None else 0
            if int(account.get("trade_mode", -1)) != int(demo_mode):
                raise MT5ExecutionError("Customer LIVE_DEMO requires an MT5 demo account.")
            if str(account.get("login")) != str(account_id):
                raise MT5ExecutionError("Connected MT5 demo account does not match account identity.")
            if not account.get("trade_allowed"):
                raise MT5ExecutionError("Connected MT5 demo account does not allow trading.")
            if hasattr(broker, "positions") and broker.positions():
                raise MT5ExecutionError("Open positions require manual review before a new demo entry.")
            balance, equity = float(account.get("balance") or 0), float(account.get("equity") or 0)
            if balance <= 0 or equity <= 0:
                raise MT5ExecutionError("Demo balance and equity must be positive.")
            drawdown_pct = max(0.0, (balance - equity) / balance * 100)
            quote = broker.quote(symbol)
            candles = broker.candles(symbol, self._timeframe(timeframe), 120)
            technical = analyze_candles(candles)
            price = float(technical.get("price") or quote.get("ask") or quote.get("bid") or 0.0)
            atr = float((technical.get("indicators") or {}).get("atr_14") or 0.0)
            if price <= 0 or atr <= 0:
                raise MT5ExecutionError("Technical data is insufficient for demo risk levels.")
            trend = str(technical.get("trend") or "neutral").lower()
            momentum = str(technical.get("momentum") or "neutral").lower()
            if trend == "bearish":
                entry = float(quote["bid"]); stop_loss = entry + 1.5 * atr; take_profit = entry - 2.5 * atr
            else:
                entry = float(quote["ask"]); stop_loss = entry - 1.5 * atr; take_profit = entry + 2.5 * atr
            tick_seconds = int(quote.get("time") or 0)
            if not tick_seconds:
                raise MT5ExecutionError("MT5 quote has no timestamp.")
            offset = int(os.getenv("ATLAS_MT5_TICK_OFFSET_SECONDS", "0"))
            if offset not in {0, 7200, 10800}:
                raise MT5ExecutionError("Unsupported broker tick clock offset.")
            market_time = datetime.fromtimestamp(tick_seconds - offset, tz=timezone.utc)
            snapshot = build_snapshot(
                context=CustomerContext(customer_id, account_id, Mode.LIVE_DEMO),
                symbol=symbol.upper(), timeframe=timeframe,
                market={
                    **quote, "timestamp": market_time.isoformat(), "trend": trend, "momentum": momentum,
                    "volatility": round((atr / price) * 100, 6),
                },
                account={**account, "drawdown_pct": drawdown_pct, "open_risk_pct": 0.0},
                system={"connector_ok": True, "latency_ms": 0},
                news=None, sentiment=None, now=datetime.now(timezone.utc),
            )
            result = CustomerRealtimeCycle(DemoAdapter(broker)).run(
                snapshot, stop_loss=stop_loss, take_profit=take_profit,
                demo_volume=demo_volume, requested_risk_pct=requested_risk_pct,
                learned_weights=learned_weights,
            )
            return {**result, "mode": "LIVE_DEMO", "symbol": symbol.upper(), "timeframe": timeframe}
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass
