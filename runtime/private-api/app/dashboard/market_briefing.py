from __future__ import annotations

import os
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
)

QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
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


class MarketBriefingService:
    """Public market context. It has no path into ATLAS execution decisions."""

    def __init__(self, session: Any = requests, timeout: float | None = None):
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

    def market_board(self) -> list[dict[str, Any]]:
        symbols = ",".join(symbol for symbol, _, _ in WALL_STREET_WATCHLIST)
        payload = self._get(QUOTE_URL, params={"symbols": symbols}).json()
        quotes = payload.get("quoteResponse", {}).get("result", [])
        by_symbol = {str(item.get("symbol", "")): item for item in quotes}

        board: list[dict[str, Any]] = []
        for symbol, label, category in WALL_STREET_WATCHLIST:
            quote = by_symbol.get(symbol, {})
            price = _number(quote.get("regularMarketPrice"))
            change = _number(quote.get("regularMarketChange"))
            change_pct = _number(quote.get("regularMarketChangePercent"))
            board.append(
                {
                    "symbol": symbol,
                    "label": label,
                    "category": category,
                    "price": price,
                    "change": change,
                    "change_percent": round(change_pct, 3) if change_pct is not None else None,
                    "market_state": quote.get("marketState", "UNKNOWN"),
                    "available": price is not None,
                }
            )
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
            "status": "ONLINE" if board else "DEGRADED",
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
