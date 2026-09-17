from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import re
from typing import Iterable


@dataclass(frozen=True)
class UniverseSymbol:
    broker_symbol: str
    canonical_symbol: str
    asset_class: str
    priority: int
    spread_points: float
    spread_ratio: float
    tradeable: bool
    visible: bool
    opportunity_score: float

    def to_dict(self) -> dict:
        return asdict(self)


# ATLAS organizes supported instruments by market category. These categories
# guide discovery and ranking; they are not a fixed "main assets" limitation.
ASSET_CATEGORIES = {
    "METALS": {
        "XAUUSD": 1,
        "XAGUSD": 1,
    },
    "ENERGY": {
        "NGAS": 1,
        "NATGAS": 1,
        "USOIL": 1,
        "WTI": 1,
        "UKOIL": 2,
        "BRENT": 2,
    },
    "FOREX": {
        "EURUSD": 1,
        "GBPUSD": 1,
        "USDJPY": 1,
        "USDCHF": 2,
        "AUDUSD": 2,
        "USDCAD": 2,
        "NZDUSD": 2,
        "EURJPY": 2,
        "GBPJPY": 2,
        "EURGBP": 3,
    },
    "INDICES": {
        "NAS100": 1,
        "USTEC": 1,
        "US500": 1,
        "SPX500": 1,
        "US30": 2,
        "GER40": 2,
        "DE40": 2,
        "UK100": 3,
    },
    "CRYPTO": {
        "BTCUSD": 1,
        "BTCUSDT": 1,
        "ETHUSD": 1,
        "ETHUSDT": 1,
        "SOLUSD": 2,
        "SOLUSDT": 2,
        "XRPUSD": 2,
        "XRPUSDT": 2,
        "BNBUSD": 3,
        "BNBUSDT": 3,
    },
}

CATEGORY_SYMBOLS = {
    symbol: (category, priority)
    for category, symbols in ASSET_CATEGORIES.items()
    for symbol, priority in symbols.items()
}

ALIASES = {
    "GOLD": "XAUUSD",
    "SILVER": "XAGUSD",
    "NATURALGAS": "NGAS",
    "NATGAS": "NGAS",
    "WTICOIL": "WTI",
    "CRUDEOIL": "WTI",
    "BRENTCASH": "BRENT",
    "NASDAQ": "NAS100",
    "NASDAQ100": "NAS100",
    "USTEC": "NAS100",
    "SP500": "US500",
    "SPX500": "US500",
    "DAX40": "GER40",
    "DE40": "GER40",
}


def normalize_symbol(symbol: str) -> str:
    token = re.sub(r"[^A-Z0-9]", "", symbol.upper())
    # Broker suffixes/prefixes frequently append m, pro, cash, etc. Prefer
    # known category symbols contained in the broker symbol.
    for canonical in sorted(CATEGORY_SYMBOLS, key=len, reverse=True):
        if canonical in token:
            return ALIASES.get(canonical, canonical)
    for alias, canonical in ALIASES.items():
        if alias in token:
            return canonical
    return token


def classify_symbol(canonical: str) -> tuple[str, int] | None:
    if canonical in CATEGORY_SYMBOLS:
        return CATEGORY_SYMBOLS[canonical]
    mapped = ALIASES.get(canonical, canonical)
    return CATEGORY_SYMBOLS.get(mapped)


def score_symbol(priority: int, spread_ratio: float, tradeable: bool) -> float:
    if not tradeable:
        return 0.0
    priority_score = {1: 55.0, 2: 45.0, 3: 35.0}.get(priority, 25.0)
    if not math.isfinite(spread_ratio) or spread_ratio < 0:
        spread_score = 0.0
    elif spread_ratio <= 0.00010:
        spread_score = 45.0
    elif spread_ratio <= 0.00050:
        spread_score = 35.0
    elif spread_ratio <= 0.00100:
        spread_score = 25.0
    elif spread_ratio <= 0.00300:
        spread_score = 15.0
    else:
        spread_score = 5.0
    return round(min(100.0, priority_score + spread_score), 2)


def build_universe(raw_symbols: Iterable[dict], top_n: int = 30) -> list[UniverseSymbol]:
    ranked: list[UniverseSymbol] = []
    seen_canonical: set[str] = set()

    for item in raw_symbols:
        broker_symbol = str(item.get("symbol", ""))
        canonical = normalize_symbol(broker_symbol)
        classified = classify_symbol(canonical)
        if not classified or canonical in seen_canonical:
            continue
        asset_class, priority = classified
        bid = float(item.get("bid", 0.0) or 0.0)
        ask = float(item.get("ask", 0.0) or 0.0)
        point = float(item.get("point", 0.0) or 0.0)
        tradeable = bool(item.get("tradeable", False)) and bid > 0 and ask > 0 and ask >= bid
        spread = ask - bid if tradeable else math.inf
        spread_points = spread / point if tradeable and point > 0 else math.inf
        mid = (ask + bid) / 2.0 if tradeable else 0.0
        spread_ratio = spread / mid if mid > 0 else math.inf
        score = score_symbol(priority, spread_ratio, tradeable)
        ranked.append(UniverseSymbol(
            broker_symbol=broker_symbol,
            canonical_symbol=canonical,
            asset_class=asset_class,
            priority=priority,
            spread_points=round(spread_points, 2) if math.isfinite(spread_points) else math.inf,
            spread_ratio=round(spread_ratio, 8) if math.isfinite(spread_ratio) else math.inf,
            tradeable=tradeable,
            visible=bool(item.get("visible", False)),
            opportunity_score=score,
        ))
        seen_canonical.add(canonical)

    ranked.sort(key=lambda x: (-x.opportunity_score, x.priority, x.canonical_symbol))
    return ranked[:max(1, int(top_n))]
