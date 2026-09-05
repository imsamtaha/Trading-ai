"""Resilient Wall Street market board and financial-news feed for ATLAS.

The feed is intentionally server-side: provider credentials are never sent to
the browser. Data freshness is labelled from configuration because a market-data
vendor plan can be delayed and must not be represented as real-time otherwise.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable


class MarketDataProviderError(RuntimeError):
    """Raised when the configured external provider cannot return usable data."""


WALL_STREET_INSTRUMENTS: tuple[dict[str, str], ...] = (
    {"symbol": "SPY", "label": "S&P 500", "group": "US Equity"},
    {"symbol": "QQQ", "label": "Nasdaq 100", "group": "US Equity"},
    {"symbol": "DIA", "label": "Dow Jones", "group": "US Equity"},
    {"symbol": "IWM", "label": "Russell 2000", "group": "US Equity"},
)


class MarketIntelligenceFeed:
    """Fetch and cache a compact market board without blocking MT5 telemetry."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_get: Callable[..., Any] | None = None,
        cache_seconds: int | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("ATLAS_FINNHUB_API_KEY", "")).strip()
        self._http_get = http_get or urllib.request.urlopen
        configured_ttl = cache_seconds if cache_seconds is not None else int(
            os.getenv("ATLAS_MARKET_CACHE_SECONDS", "60")
        )
        self.cache_seconds = max(30, configured_ttl)
        self._now = now or time.time
        self._cached_at = 0.0
        self._cached_snapshot: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def snapshot(self) -> dict[str, Any]:
        """Return a cached provider snapshot or a non-fatal configuration state."""
        if not self.is_configured:
            return self._not_configured()

        with self._lock:
            current = self._now()
            if self._cached_snapshot and current - self._cached_at < self.cache_seconds:
                return {**self._cached_snapshot, "cached": True}

            snapshot = self._fetch_snapshot()
            self._cached_snapshot = snapshot
            self._cached_at = current
            return snapshot

    def _not_configured(self) -> dict[str, Any]:
        return {
            "status": "NOT_CONFIGURED",
            "source": "Finnhub",
            "data_label": "Provider connection required",
            "delayed": True,
            "cached": False,
            "generated_at": _iso_now(),
            "markets": [],
            "news": [],
            "message": "Set ATLAS_FINNHUB_API_KEY to activate the Wall Street board and financial news.",
        }

    def _fetch_snapshot(self) -> dict[str, Any]:
        markets: list[dict[str, Any]] = []
        errors: list[str] = []

        for instrument in WALL_STREET_INSTRUMENTS:
            try:
                quote = self._fetch_json("/quote", {"symbol": instrument["symbol"]})
                last = _number(quote.get("c"))
                if last is None:
                    raise MarketDataProviderError("provider returned no current price")
                markets.append(
                    {
                        **instrument,
                        "last": last,
                        "change": _number(quote.get("d")),
                        "change_percent": _number(quote.get("dp")),
                        "as_of": _epoch_to_iso(quote.get("t")),
                    }
                )
            except MarketDataProviderError as exc:
                errors.append(f"{instrument['symbol']}: {exc}")

        news: list[dict[str, Any]] = []
        try:
            raw_news = self._fetch_json("/news", {"category": "general"})
            if not isinstance(raw_news, list):
                raise MarketDataProviderError("provider returned invalid news data")
            news = [
                {
                    "headline": str(item.get("headline", "")).strip(),
                    "source": str(item.get("source", "Market news")).strip(),
                    "url": str(item.get("url", "")).strip(),
                    "summary": str(item.get("summary", "")).strip(),
                    "published_at": _epoch_to_iso(item.get("datetime")),
                }
                for item in raw_news
                if isinstance(item, dict) and str(item.get("headline", "")).strip()
            ][:6]
        except MarketDataProviderError as exc:
            errors.append(f"news: {exc}")

        if not markets:
            return {
                "status": "DEGRADED",
                "source": "Finnhub",
                "data_label": self._data_label(),
                "delayed": self._is_delayed(),
                "cached": False,
                "generated_at": _iso_now(),
                "markets": [],
                "news": news,
                "message": "Market data provider is unavailable. MT5 telemetry remains independent.",
                "errors": errors,
            }

        return {
            "status": "LIVE" if not errors else "DEGRADED",
            "source": "Finnhub",
            "data_label": self._data_label(),
            "delayed": self._is_delayed(),
            "cached": False,
            "generated_at": _iso_now(),
            "markets": markets,
            "news": news,
            "message": None if not errors else "Some provider data could not be refreshed.",
            "errors": errors,
        }

    def _fetch_json(self, endpoint: str, params: dict[str, str]) -> Any:
        query = urllib.parse.urlencode({**params, "token": self.api_key})
        request = urllib.request.Request(
            f"https://finnhub.io/api/v1{endpoint}?{query}",
            headers={"Accept": "application/json", "User-Agent": "ATLAS/1.2"},
        )
        try:
            with self._http_get(request, timeout=10) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MarketDataProviderError(str(exc)) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MarketDataProviderError("provider returned invalid JSON") from exc

        if isinstance(data, dict) and data.get("error"):
            raise MarketDataProviderError(str(data["error"]))
        return data

    def _is_delayed(self) -> bool:
        return os.getenv("ATLAS_MARKET_DATA_DELAYED", "true").lower() == "true"

    def _data_label(self) -> str:
        return "Delayed provider data" if self._is_delayed() else "Provider data"


def _number(value: object) -> float | None:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _epoch_to_iso(value: object) -> str | None:
    try:
        timestamp = int(value)
        if timestamp <= 0:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
