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


CORE_CANONICAL = {
    "XAUUSD": ("METALS", 1),
    "XAGUSD": ("METALS", 1),
    "NGAS": ("ENERGY", 1),
    "NATGAS": ("ENERGY", 1),
    "USOIL": ("ENERGY", 1),
    "WTI": ("ENERGY", 1),
    "UKOIL": ("ENERGY", 2),
    "BRENT": ("ENERGY", 2),
    "EURUSD": ("FOREX", 1),
    "GBPUSD": ("FOREX", 1),
    "USDJPY": ("FOREX", 1),
    "USDCHF": ("FOREX", 2),
    "AUDUSD": ("FOREX", 2),
    "USDCAD": ("FOREX", 2),
    "NZDUSD": ("FOREX", 2),
    "EURJPY": ("FOREX", 2),
    "GBPJPY": ("FOREX", 2),
    "EURGBP": ("FOREX", 3),
    "NAS100": ("INDICES", 1),
    "USTEC": ("INDICES", 1),
    "US500": ("INDICES", 1),
    "SPX500": ("INDICES", 1),
    "US30": ("INDICES", 2),
    "GER40": ("INDICES", 2),
    "DE40": ("INDICES", 2),
    "UK100": ("INDICES", 3),
    "JP225": ("INDICES", 2),
    "HK50": ("INDICES", 3),
    "EU50": ("INDICES", 2),
    "FRA40": ("INDICES", 3),
    "US2000": ("INDICES", 3),
    "AUDJPY": ("FOREX", 3),
    "EURCAD": ("FOREX", 3),
    "CADJPY": ("FOREX", 3),
    "BTCUSD": ("CRYPTO", 1),
    "BTCUSDT": ("CRYPTO", 1),
    "ETHUSD": ("CRYPTO", 1),
    "ETHUSDT": ("CRYPTO", 1),
    "SOLUSD": ("CRYPTO", 2),
    "SOLUSDT": ("CRYPTO", 2),
    "XRPUSD": ("CRYPTO", 2),
    "XRPUSDT": ("CRYPTO", 2),
    "BNBUSD": ("CRYPTO", 3),
    "BNBUSDT": ("CRYPTO", 3),
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
    "JAPAN225": "JP225",
    "HONGKONG50": "HK50",
    "EURO50": "EU50",
    "FRANCE40": "FRA40",
}


def normalize_symbol(symbol: str) -> str:
    token = re.sub(r"[^A-Z0-9]", "", symbol.upper())
    # Broker suffixes/prefixes frequently append m, pro, cash, etc. Prefer
    # known canonical tokens contained in the broker symbol.
    for canonical in sorted(CORE_CANONICAL, key=len, reverse=True):
        if canonical in token:
            return ALIASES.get(canonical, canonical)
    for alias, canonical in ALIASES.items():
        if alias in token:
            return canonical
    return token


def classify_symbol(canonical: str) -> tuple[str, int] | None:
    if canonical in CORE_CANONICAL:
        return CORE_CANONICAL[canonical]
    # Normalize aliases that map onto entries not explicitly duplicated.
    mapped = ALIASES.get(canonical, canonical)
    return CORE_CANONICAL.get(mapped)


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
