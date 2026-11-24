"""Read-only cTrader demo market data for the PAPER worker."""

from __future__ import annotations

import time
from contextlib import ExitStack
from typing import Any

from websockets.sync.client import ClientConnection

from app.execution.provider_mode import ctrader_selected
from app.integrations.ctrader_demo import (
    HEARTBEAT,
    DemoConnectionError,
    DemoCredentials,
    _receive,
    _request,
    _send,
    _verify_account,
    demo_session,
)

SYMBOLS_LIST = (2114, 2115)
SUBSCRIBE_SPOTS = (2127, 2128)
SPOT_EVENT = 2131
TREND_BARS = (2137, 2138)
PERIODS = {
    "1m": (1, "M1", 60), "5m": (5, "M5", 300), "15m": (7, "M15", 900),
    "30m": (8, "M30", 1800), "1h": (9, "H1", 3600), "4h": (10, "H4", 14400),
    "1d": (12, "D1", 86400),
}
MAX_CANDLES = 500
PRICE_SCALE = 100_000


def _integer(value: Any, *, minimum: int = 0) -> int:
    if type(value) is int and minimum <= value < 2**63:
        return value
    if isinstance(value, str) and len(value) <= 19 and value.isascii() and value.isdecimal():
        return _integer(int(value), minimum=minimum)
    raise DemoConnectionError("INVALID_PROVIDER_NUMBER")


class CTraderMarketData:
    """Authenticated demo data session with closed bars and timestamped bid/ask."""

    def __init__(self) -> None:
        self._connection = ExitStack()
        self._session: ClientConnection | None = None
        self._account_id = 0
        self._symbols: dict[str, int] = {}
        self._subscribed: set[int] = set()
        self._spots: dict[int, dict[str, tuple[int, int]]] = {}
        self._heartbeat_at = 0.0
        self._last_history_at = 0.0

    def connect(self) -> None:
        if not ctrader_selected():
            raise DemoConnectionError("CTRADER_PROVIDER_NOT_SELECTED")
        self.disconnect()
        credentials = DemoCredentials.from_env()
        try:
            self._session, self._account_id = self._connection.enter_context(demo_session(credentials))
            self._heartbeat_at = time.monotonic()
            payload = self._call(SYMBOLS_LIST, {})
            rows = payload.get("symbol")
            if not isinstance(rows, list):
                raise DemoConnectionError("INVALID_SYMBOL_LIST")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("symbolName"), str):
                    raise DemoConnectionError("INVALID_SYMBOL_LIST")
                if row.get("enabled") is False:
                    continue
                name = row["symbolName"]
                if name in self._symbols:
                    raise DemoConnectionError("AMBIGUOUS_SYMBOL_LIST")
                self._symbols[name] = _integer(row.get("symbolId"), minimum=1)
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        try:
            self._connection.close()
        finally:
            self._session = None
            self._account_id = 0
            self._symbols.clear()
            self._subscribed.clear()
            self._spots.clear()

    def _symbol(self, name: str) -> int:
        if name not in self._symbols:
            raise DemoConnectionError("SYMBOL_NOT_AVAILABLE")
        return self._symbols[name]

    def _session_with_heartbeat(self) -> ClientConnection:
        if self._session is None:
            raise DemoConnectionError("PROVIDER_NOT_CONNECTED")
        now = time.monotonic()
        if now - self._heartbeat_at >= 8:
            _send(self._session, {"payloadType": HEARTBEAT, "payload": {}})
            self._heartbeat_at = now
        return self._session

    def _call(self, types: tuple[int, int], payload: dict[str, Any]) -> dict[str, Any]:
        response = _request(
            self._session_with_heartbeat(), types,
            {"ctidTraderAccountId": self._account_id, **payload},
            time.monotonic() + 8, on_event=self._event,
        )
        _verify_account(response, self._account_id)
        return response

    def _event(self, message: dict[str, Any]) -> None:
        if message.get("payloadType") != SPOT_EVENT:
            return
        value = message.get("payload")
        if not isinstance(value, dict):
            raise DemoConnectionError("INVALID_SPOT_EVENT")
        _verify_account(value, self._account_id)
        symbol_id = _integer(value.get("symbolId"), minimum=1)
        if symbol_id not in self._subscribed or value.get("timestamp") is None:
            return
        stamp = _integer(value["timestamp"], minimum=1)
        now = time.time() * 1000
        if not now - 30_000 <= stamp <= now + 5_000:
            return
        spot = self._spots.setdefault(symbol_id, {})
        for side in ("bid", "ask"):
            if side in value and stamp >= spot.get(side, (0, 0))[1]:
                spot[side] = (_integer(value[side], minimum=1), stamp)

    def quote(self, symbol: str) -> dict[str, Any]:
        symbol_id = self._symbol(symbol)
        if symbol_id not in self._subscribed:
            self._subscribed.add(symbol_id)
            try:
                self._call(SUBSCRIBE_SPOTS, {"symbolId": [symbol_id], "subscribeToSpotTimestamp": True})
            except DemoConnectionError:
                self._subscribed.discard(symbol_id)
                self._spots.pop(symbol_id, None)
                raise
        deadline = time.monotonic() + 8
        while (remaining := deadline - time.monotonic()) > 0:
            spot = self._spots.get(symbol_id, {})
            if "bid" in spot and "ask" in spot:
                bid, bid_at = spot["bid"]
                ask, ask_at = spot["ask"]
                stamp = min(bid_at, ask_at)
                if ask >= bid and time.time() * 1000 - stamp <= 30_000:
                    return {"symbol": symbol, "bid": bid / PRICE_SCALE, "ask": ask / PRICE_SCALE,
                            "time_msc": stamp}
            self._event(_receive(self._session_with_heartbeat(), remaining))
        raise DemoConnectionError("CURRENT_TWO_SIDED_QUOTE_UNAVAILABLE")

    def candles(self, symbol: str, interval: str, count: int) -> list[dict[str, Any]]:
        if interval not in PERIODS or not 1 <= count <= MAX_CANDLES:
            raise DemoConnectionError("UNSUPPORTED_HISTORY_REQUEST")
        symbol_id = self._symbol(symbol)
        period, period_name, seconds = PERIODS[interval]
        duration = seconds * 1000
        closed_before = int(time.time() * 1000) // duration * duration
        delay = 0.25 - (time.monotonic() - self._last_history_at)
        if delay > 0:
            time.sleep(delay)
        self._last_history_at = time.monotonic()
        response = self._call(TREND_BARS, {
            "symbolId": symbol_id, "period": period, "count": count,
            "fromTimestamp": max(0, closed_before - 4 * count * duration),
            "toTimestamp": closed_before - 1,
        })
        if "symbolId" in response and _integer(response["symbolId"], minimum=1) != symbol_id:
            raise DemoConnectionError("SYMBOL_ID_MISMATCH")
        if response.get("period") != period_name and _integer(response.get("period"), minimum=1) != period:
            raise DemoConnectionError("PERIOD_MISMATCH")
        rows = response.get("trendbar", [])
        if not isinstance(rows, list):
            raise DemoConnectionError("INVALID_TREND_BARS")
        bars: dict[int, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise DemoConnectionError("INVALID_TREND_BARS")
            opened = _integer(row.get("utcTimestampInMinutes"), minimum=1) * 60_000
            if opened + duration > closed_before:
                continue
            low = _integer(row.get("low"), minimum=1)
            opening, high, close = [
                low + _integer(row.get(field, 0)) for field in ("deltaOpen", "deltaHigh", "deltaClose")
            ]
            if max(opening, close) > high:
                raise DemoConnectionError("INVALID_OHLC")
            bar = {
                "open_time": opened, "close_time": opened + duration,
                "open": opening / PRICE_SCALE, "high": high / PRICE_SCALE,
                "low": low / PRICE_SCALE, "close": close / PRICE_SCALE,
                "volume": _integer(row.get("volume")),
            }
            if opened in bars and bars[opened] != bar:
                raise DemoConnectionError("CONFLICTING_TREND_BARS")
            bars[opened] = bar
        return [bars[opened] for opened in sorted(bars)[-count:]]
