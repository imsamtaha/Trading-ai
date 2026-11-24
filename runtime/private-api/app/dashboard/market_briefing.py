from __future__ import annotations

import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests


class MarketBriefingError(RuntimeError):
    pass


WALL_STREET_WATCHLIST = (
    ("^DJI", "Dow Jones", "US Equities"),
    ("^GSPC", "S&P 500", "US Equities"),
    ("^IXIC", "Nasdaq Composite", "US Equities"),
    ("^VIX", "CBOE VIX", "Volatility"),
    ("GC=F", "Gold Futures", "Commodities"),
    ("SI=F", "Silver Futures", "Commodities"),
    ("CL=F", "WTI Crude", "Commodities"),
    ("NG=F", "Natural Gas", "Commodities"),
    ("EURUSD=X", "EUR/USD", "FX"),
    ("BTC-USD", "Bitcoin", "Digital Assets"),
    ("ETH-USD", "Ethereum", "Digital Assets"),
    ("SOL-USD", "Solana", "Digital Assets"),
    ("JPY=X", "USD/JPY", "FX"),
    ("HG=F", "Copper Futures", "Commodities"),
)

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADLINES_URL = "https://www.cnbc.com/id/15839135/device/rss/rss.html"
ARABIC_HEADLINE_FEEDS = (
    ("https://alikhbariya.net/feeds/topics/economy.xml", "الإخبارية - اقتصاد"),
    ("https://alikhbariya.net/feeds/topics/markets.xml", "الإخبارية - أسواق"),
    ("https://alikhbariya.net/feeds/topics/business.xml", "الإخبارية - شركات وأعمال"),
)


def _enabled() -> bool:
    return os.getenv("ATLAS_MARKET_DATA_ENABLED", "true").lower() == "true"


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _direction(p):
    if p is None:return"NEUTRAL"
    return"BULLISH" if p>0.15 else"BEARISH" if p<-0.15 else"NEUTRAL"
def _freshness(timestamp):
    if not timestamp:return None,"UNKNOWN",False
    try:ts=datetime.fromtimestamp(float(timestamp),tz=timezone.utc);age=max(0,(datetime.now(timezone.utc)-ts).total_seconds())
    except(TypeError,ValueError,OverflowError):return None,"UNKNOWN",False
    fresh_limit=max(60,int(os.getenv("ATLAS_MARKET_FRESH_SECONDS","900")));stale_limit=max(fresh_limit,int(os.getenv("ATLAS_MARKET_STALE_SECONDS","86400")))
    state="FRESH" if age<=fresh_limit else"DELAYED" if age<=stale_limit else"STALE"
    return ts.isoformat(),state,state!="STALE"

class MarketBriefingService:
    """Public market context. It has no path into ATLAS execution decisions."""

    def __init__(self, session: Any = requests, timeout: float | None = None):
        self._market_lock = RLock()
        self._board_cache = None
        self._board_cached_at = 0.0
        self.session = session
        self.timeout = timeout or float(os.getenv("ATLAS_MARKET_DATA_TIMEOUT", "8"))

    def _get(self, url: str, **kwargs: Any) -> Any:
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": "ATLAS-MarketBoard/1.0"},
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise MarketBriefingError(str(exc)) from exc

    def _chart_quote(self, symbol):
        try:
            payload = self._get(CHART_URL.format(symbol=quote(symbol, safe="")),
                                params={"range": "5d", "interval": "1d", "includePrePost": "false"}).json()
            item = payload["chart"]["result"][0]
            meta = item.get("meta", {})
            quotes = item.get("indicators", {}).get("quote") or [{}]
            closes = [value for entry in (quotes[0].get("close") or [])
                      if (value := _number(entry)) is not None and math.isfinite(value) and value > 0]
            price = _number(meta.get("regularMarketPrice"))
            if price is None or not math.isfinite(price) or price <= 0:
                price = closes[-1] if closes else None
                quote_time, freshness, fresh = None, "UNKNOWN", False
            else:
                quote_time, freshness, fresh = _freshness(meta.get("regularMarketTime"))
            # chartPreviousClose is the close before the full requested range.
            previous = closes[-2] if len(closes) >= 2 else None
            change = price - previous if price is not None and previous is not None else None
            pct = round(change / previous * 100, 3) if change is not None else None
            return price, change, pct, quote_time, freshness, fresh
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            raise MarketBriefingError("Invalid market chart response") from exc

    def _market_row(self, instrument):
        symbol, label, category = instrument
        try:
            price, change, pct, quote_time, freshness, fresh = self._chart_quote(symbol)
        except MarketBriefingError:
            price = change = pct = quote_time = None
            freshness, fresh = "UNAVAILABLE", False
        return {
            "symbol": symbol, "label": label, "category": category, "provider": "Yahoo Finance",
            "price": price, "change": change, "change_percent": pct, "quote_time": quote_time,
            "freshness": freshness, "fresh": fresh, "market_state": freshness,
            "direction": _direction(pct) if fresh and pct is not None else "UNAVAILABLE",
            "analysis": ("UP" if pct > 0 else "DOWN" if pct < 0 else "FLAT") if fresh and pct is not None else "UNAVAILABLE",
            "available": price is not None,
        }

    def market_board(self):
        with self._market_lock:
            now = time.monotonic()
            ttl = max(15, int(os.getenv("ATLAS_MARKET_CACHE_SECONDS", "60")))
            if self._board_cache is not None and now - self._board_cached_at < ttl:
                return self._board_cache
            with ThreadPoolExecutor(max_workers=7) as pool:
                board = list(pool.map(self._market_row, WALL_STREET_WATCHLIST))
            self._board_cache = board
            self._board_cached_at = time.monotonic()
            return board

    def headlines(self, limit: int = 3, language: str = "en") -> list[dict[str, str]]:
        if language == "ar":
            return self.arabic_headlines(limit=limit)

        response = self._get(HEADLINES_URL)
        return self._parse_rss_items(
            response.content,
            limit=limit,
            fallback_source="CNBC Markets",
        )

    def arabic_headlines(self, limit: int = 3) -> list[dict[str, str]]:
        stories: list[dict[str, str]] = []
        per_feed_limit = max(1, min(20, limit))

        for feed_url, source_label in ARABIC_HEADLINE_FEEDS:
            response = self._get(feed_url)
            stories.extend(
                self._parse_rss_items(
                    response.content,
                    limit=per_feed_limit,
                    fallback_source=source_label,
                )
            )
            if len(stories) >= max(1, min(20, limit)):
                break

        return stories[: max(1, min(20, limit))]

    def _parse_rss_items(
        self,
        content: bytes,
        *,
        limit: int,
        fallback_source: str,
    ) -> list[dict[str, str]]:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise MarketBriefingError("Market headline feed returned invalid XML.") from exc

        stories: list[dict[str, str]] = []
        for item in root.iter():
            if item.tag.rsplit("}", 1)[-1] != "item":
                continue
            values = {
                child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
                for child in item
            }
            if values.get("title"):
                stories.append(
                    {
                        "title": values["title"],
                        "url": values.get("link", ""),
                        "published_at": values.get("pubDate", ""),
                        "source": values.get("source") or fallback_source,
                    }
                )
            if len(stories) >= max(1, min(20, limit)):
                break
        return stories

    def briefing(self, language: str = "en") -> dict[str, Any]:
        language = "ar" if language.lower().startswith("ar") else "en"
        if not _enabled():
            return {
                "status": "DISABLED",
                "as_of": datetime.now(timezone.utc).isoformat(),
                "market_board": [],
                "headlines": [],
                "errors": [],
                "disclaimer": "Public market context is disabled.",
            }

        errors: list[str] = []
        try:
            board = self.market_board()
        except MarketBriefingError as exc:
            board = []
            errors.append("market_board: " + str(exc))
        try:
            headlines = self.headlines(language=language)
        except MarketBriefingError as exc:
            headlines = []
            errors.append("headlines: " + str(exc))

        return {
            "status": "ONLINE" if any(row["fresh"] for row in board) else "DEGRADED",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "market_board": board,
            "headlines": headlines,
            "errors": errors,
            "language": language,
            "source": (
                "Yahoo Finance public market data and Arabic RSS sources"
                if language == "ar"
                else "Yahoo Finance public market data and RSS"
            ),
            "disclaimer": (
                "Context only. Public prices and headlines are not ATLAS signals and "
                "are never used by the execution gate."
            ),
        }


_service = MarketBriefingService()


def get_market_briefing(language: str = "en") -> dict[str, Any]:
    return _service.briefing(language=language)
