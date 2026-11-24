"""Serve sanitized cTrader demo quotes to the ATLAS dashboards over a private bridge."""

from __future__ import annotations

import hmac
import os
import threading
import time

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from app.integrations.ctrader_demo import DemoConnectionError
from app.integrations.ctrader_market import CTraderMarketData

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
SYMBOLS = frozenset(("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "LTCUSD",
                     "DOGEUSD", "AVAXUSD", "LINKUSD", "EURUSD", "GBPUSD", "XAUUSD"))
INTERVALS = {60: "1h", 240: "4h", 1440: "1d", 10080: None}
_cache: dict[tuple[str, int], tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_sessions = threading.BoundedSemaphore(2)


def market_snapshot(asset: str, interval: int) -> dict:
    provider = CTraderMarketData()
    quote, candles, reason = None, [], "SYMBOL_UNAVAILABLE"
    try:
        provider.connect()
        try:
            tick = provider.quote(asset)
        except DemoConnectionError as exc:
            if str(exc) != "SYMBOL_NOT_AVAILABLE":
                reason = "CURRENT_QUOTE_UNAVAILABLE"
        else:
            quote = {"bid": tick["bid"], "ask": tick["ask"], "timeMsc": tick["time_msc"]}

        timeframe = INTERVALS[interval]
        if timeframe and (quote or reason != "SYMBOL_UNAVAILABLE"):
            try:
                bars = provider.candles(asset, timeframe, count=120)
            except DemoConnectionError:
                pass
            else:
                candles = [
                    {"time": bar["open_time"] // 1000, **{key: bar[key] for key in ("open", "high", "low", "close")}}
                    for bar in bars
                ]
    finally:
        provider.disconnect()
    return {"schema": "atlas-ctrader-market-v1", "source": "ctrader-demo", "environment": "DEMO",
            "access": "VIEW_ONLY", "asset": asset, "interval": interval, "quote": quote,
            "quoteReason": None if quote else reason, "candles": candles}


@app.get("/api/ctrader/market-data")
def market_data(asset: str, interval: int, authorization: str | None = Header(default=None)) -> JSONResponse:
    token = os.getenv("ATLAS_CTRADER_MARKET_TOKEN", "")
    if not token or not hmac.compare_digest((authorization or "").encode(), ("Bearer " + token).encode()):
        raise HTTPException(401, "BRIDGE_AUTH_REQUIRED")
    if asset not in SYMBOLS or interval not in INTERVALS:
        raise HTTPException(400, "INVALID_MARKET_REQUEST")
    key = (asset, interval)
    with _cache_lock:
        cached = _cache.get(key)
        if cached and time.monotonic() < cached[0]:
            return JSONResponse(cached[1], headers={"Cache-Control": "no-store"})
    if not _sessions.acquire(blocking=False):
        raise HTTPException(503, "BRIDGE_BUSY")
    try:
        result = market_snapshot(asset, interval)
        with _cache_lock:
            _cache[key] = (time.monotonic() + 12, result)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except DemoConnectionError:
        raise HTTPException(503, "CTRADER_DEMO_UNAVAILABLE") from None
    finally:
        _sessions.release()
