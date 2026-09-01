from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None


TIMEFRAME_MAP = {
    "1m": "TIMEFRAME_M1",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30",
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}


class MT5MarketData:
    """Read-only MT5 market-data adapter."""

    def __init__(self, terminal_path: str | None = None):
        self.terminal_path = terminal_path
        self.connected = False

    def connect(self) -> bool:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not installed.")
        kwargs = {"path": self.terminal_path} if self.terminal_path else {}
        self.connected = bool(mt5.initialize(**kwargs))
        return self.connected

    def close(self) -> None:
        if mt5 is not None and self.connected:
            mt5.shutdown()
        self.connected = False

    def _require(self) -> None:
        if not self.connected:
            raise RuntimeError("MT5 is not connected. Call connect() first.")

    def candles(self, symbol: str, timeframe: str, limit: int = 200) -> dict[str, Any]:
        self._require()
        if timeframe not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported MT5 timeframe: {timeframe}")
        if not 1 <= limit <= 5000:
            raise ValueError("limit must be between 1 and 5000")

        symbol = symbol.upper()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {mt5.last_error()}")

        timeframe_value = getattr(mt5, TIMEFRAME_MAP[timeframe])
        rates = mt5.copy_rates_from_pos(symbol, timeframe_value, 0, limit)
        if rates is None:
            raise RuntimeError(f"MT5 copy_rates_from_pos failed for {symbol}: {mt5.last_error()}")

        candles = [
            {
                "open_time": int(row["time"] * 1000),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["tick_volume"]),
                "close_time": int(row["time"] * 1000),
            }
            for row in rates
        ]

        return {
            "symbol": symbol,
            "interval": timeframe,
            "count": len(candles),
            "source": "mt5",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "candles": candles,
        }

    def price(self, symbol: str) -> dict[str, Any]:
        self._require()
        symbol = symbol.upper()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {mt5.last_error()}")
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"MT5 tick unavailable for {symbol}: {mt5.last_error()}")
        bid = float(tick.bid)
        ask = float(tick.ask)
        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "price": (bid + ask) / 2 if bid and ask else float(tick.last),
            "time": int(tick.time),
        }
