"""View-only market data from an authorized cTrader demo account."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from websockets.sync.client import ClientConnection

from app.integrations.ctrader_demo import DemoConnectionError, _receive, _request


SYMBOLS = (2114, 2115)
SUBSCRIBE_SPOTS = (2127, 2128)
SPOT_EVENT = 2131
HISTORICAL_BARS = (2137, 2138)
HEARTBEAT = 51
PRICE_SCALE = 100_000
PERIODS = {
    "1m": ("M1", 1, 60),
    "5m": ("M5", 5, 300),
    "15m": ("M15", 7, 900),
    "30m": ("M30", 8, 1800),
    "1h": ("H1", 9, 3600),
    "4h": ("H4", 10, 14400),
    "1d": ("D1", 12, 86400),
}


def _integer(value: Any, *, minimum: int) -> int:
    digits = str(value)
    if len(digits) > 19 or not digits.isascii() or not digits.isdecimal() or int(digits) < minimum:
        raise DemoConnectionError("INVALID_MARKET_DATA")
    return int(digits)


class CTraderDemoMarket:
    """A single demo session, with spot messages demultiplexed from replies."""

    def __init__(self, session: ClientConnection, account_id: int, max_quote_age: int) -> None:
        self.session = session
        self.account_id = account_id
        self.max_quote_age = max_quote_age
        self.symbol_ids: dict[str, int] = {}
        self.spots: dict[int, dict[str, tuple[int, int]]] = {}
        self.last_heartbeat = time.monotonic()

    def _keepalive(self) -> None:
        if time.monotonic() - self.last_heartbeat >= 8:
            self.session.send(json.dumps({"payloadType": HEARTBEAT, "payload": {}}))
            self.last_heartbeat = time.monotonic()

    def _remember_spot(self, message: dict[str, Any]) -> None:
        if message.get("payloadType") != SPOT_EVENT:
            return
        payload = message.get("payload")
        if not isinstance(payload, dict) or str(payload.get("ctidTraderAccountId")) != str(self.account_id):
            return
        try:
            symbol_id = _integer(payload.get("symbolId"), minimum=1)
            timestamp = _integer(payload.get("timestamp"), minimum=1)
            sides = {side: _integer(payload[side], minimum=1) for side in ("bid", "ask") if side in payload}
        except DemoConnectionError:
            return
        if symbol_id not in self.spots or timestamp > time.time() * 1000 + 5000:
            return
        prices = self.spots[symbol_id]
        for side, price in sides.items():
            if side not in prices or timestamp >= prices[side][1]:
                prices[side] = price, timestamp

    def _request(self, types: tuple[int, int], **payload: Any) -> dict[str, Any]:
        self._keepalive()
        result = _request(
            self.session, types, {"ctidTraderAccountId": self.account_id, **payload},
            time.monotonic() + 5, self._remember_spot,
        )
        if str(result.get("ctidTraderAccountId")) != str(self.account_id):
            raise DemoConnectionError("ACCOUNT_ID_MISMATCH")
        return result

    def subscribe(self, names: list[str]) -> None:
        rows = self._request(SYMBOLS).get("symbol", [])
        if not isinstance(rows, list):
            raise DemoConnectionError("INVALID_MARKET_DATA")
        wanted = set(names)
        for row in rows:
            if not isinstance(row, dict) or row.get("enabled") is False:
                continue
            name = row.get("symbolName")
            if not isinstance(name, str) or name not in wanted:
                continue
            if name in self.symbol_ids:
                raise DemoConnectionError("AMBIGUOUS_CTRADER_SYMBOL")
            self.symbol_ids[name] = _integer(row.get("symbolId"), minimum=1)
        if self.symbol_ids.keys() != wanted:
            raise DemoConnectionError("CTRADER_SYMBOL_NOT_AVAILABLE")
        self.spots = {symbol_id: {} for symbol_id in self.symbol_ids.values()}
        self._request(SUBSCRIBE_SPOTS, symbolId=list(self.spots), subscribeToSpotTimestamp=True)

    def quote(self, symbol: str) -> dict[str, Any]:
        prices = self.spots[self.symbol_ids[symbol]]
        deadline = time.monotonic() + 3
        while True:
            if "bid" in prices and "ask" in prices:
                bid, bid_at = prices["bid"]
                ask, ask_at = prices["ask"]
                quoted_at = min(bid_at, ask_at)
                if bid <= ask and time.time() * 1000 - quoted_at <= self.max_quote_age * 1000:
                    return {"bid": bid / PRICE_SCALE, "ask": ask / PRICE_SCALE, "time_msc": quoted_at}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DemoConnectionError("NO_FRESH_CTRADER_QUOTE")
            self._keepalive()
            try:
                self._remember_spot(_receive(self.session, remaining))
            except DemoConnectionError as exc:
                if str(exc) == "PROVIDER_TIMEOUT":
                    raise DemoConnectionError("NO_FRESH_CTRADER_QUOTE") from None
                raise

    def candles(self, symbol: str, interval: str, count: int) -> list[dict[str, Any]]:
        name, period, seconds = PERIODS[interval]
        now = int(time.time())
        symbol_id = self.symbol_ids[symbol]
        response = self._request(
            HISTORICAL_BARS, symbolId=symbol_id, period=period,
            toTimestamp=now * 1000, count=count + 1,
        )
        if response.get("period") not in (period, name) or (
            "symbolId" in response and str(response["symbolId"]) != str(symbol_id)
        ):
            raise DemoConnectionError("INVALID_MARKET_DATA")
        rows = response.get("trendbar", [])
        if not isinstance(rows, list):
            raise DemoConnectionError("INVALID_MARKET_DATA")
        candles = {}
        for row in rows:
            if not isinstance(row, dict):
                raise DemoConnectionError("INVALID_MARKET_DATA")
            opened_at = _integer(row.get("utcTimestampInMinutes"), minimum=1) * 60
            if opened_at + seconds > now:
                continue
            low = _integer(row.get("low"), minimum=1)
            deltas = {key: _integer(row.get(field, 0), minimum=0) for key, field in (
                ("open", "deltaOpen"), ("close", "deltaClose"), ("high", "deltaHigh"),
            )}
            if max(deltas["open"], deltas["close"]) > deltas["high"] or opened_at in candles:
                raise DemoConnectionError("INVALID_MARKET_DATA")
            candles[opened_at] = {
                "timestamp": datetime.fromtimestamp(opened_at, tz=timezone.utc).isoformat(),
                "low": low / PRICE_SCALE,
                "volume": _integer(row.get("volume"), minimum=0),
                **{key: (low + delta) / PRICE_SCALE for key, delta in deltas.items()},
            }
        if candles and now - max(candles) > 3 * seconds:
            raise DemoConnectionError("STALE_CTRADER_CANDLES")
        return [candles[opened_at] for opened_at in sorted(candles)[-count:]]
