from dataclasses import dataclass


@dataclass(frozen=True)
class AssetConfig:
    symbol: str
    category: str
    spread_pct: float
    min_rr: float
    max_risk_pct: float


ASSETS = {
    "GOLD": AssetConfig(
        symbol="GOLD",
        category="METAL",
        spread_pct=0.05,
        min_rr=1.5,
        max_risk_pct=1.0,
    ),
    "SILVER": AssetConfig(
        symbol="SILVER",
        category="METAL",
        spread_pct=0.10,
        min_rr=1.5,
        max_risk_pct=1.0,
    ),
    "GAS": AssetConfig(
        symbol="GAS",
        category="ENERGY",
        spread_pct=0.20,
        min_rr=1.5,
        max_risk_pct=0.75,
    ),
    "EURUSD": AssetConfig(
        symbol="EURUSD",
        category="FOREX",
        spread_pct=0.02,
        min_rr=1.5,
        max_risk_pct=1.0,
    ),
    "XRPUSDT": AssetConfig(
        symbol="XRPUSDT",
        category="CRYPTO",
        spread_pct=0.05,
        min_rr=1.5,
        max_risk_pct=0.75,
    ),
    "SOLUSDT": AssetConfig(
        symbol="SOLUSDT",
        category="CRYPTO",
        spread_pct=0.05,
        min_rr=1.5,
        max_risk_pct=0.75,
    ),
}


TIMEFRAMES = ("5m", "15m", "30m", "1h")


TIMEFRAME_WEIGHTS = {
    "1h": 0.30,
    "30m": 0.25,
    "15m": 0.25,
    "5m": 0.20,
}


MIN_TRADE_SCORE = 70.0
STRONG_TRADE_SCORE = 80.0
