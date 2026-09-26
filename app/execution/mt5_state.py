"""Read-only MT5 state for the Trader Cockpit.

This adapter exposes account, position, quote state, and low-risk validation
settings only. It never places or closes orders. Live execution remains
controlled separately by ATLAS_LIVE_TRADING and the execution gateway.
"""
from __future__ import annotations

from typing import Any

from app.execution.mt5 import MT5Broker, MT5ExecutionError


ASSET_GROUPS: dict[str, tuple[str, ...]] = {
    "METALS": ("XAUUSD", "XAGUSD"),
    "ENERGY": ("GAS", "WTI", "BRENT"),
    "FOREX_MAJORS": (
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    ),
    "CRYPTO": (
        "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD",
        "LTCUSD", "BCHUSD", "DOTUSD", "LINKUSD", "AVAXUSD", "MATICUSD", "POLUSD",
        "TRXUSD", "UNIUSD", "ATOMUSD", "XLMUSD", "NEARUSD", "APTUSD", "FILUSD",
    ),
}

DEFAULT_REQUESTED_SYMBOLS: tuple[str, ...] = tuple(
    symbol for symbols in ASSET_GROUPS.values() for symbol in symbols
)

SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "XAUUSD": ("XAUUSD", "GOLD", "XAUUSD.", "XAUUSDm", "XAUUSD.a"),
    "XAGUSD": ("XAGUSD", "SILVER", "XAGUSD.", "XAGUSDm", "XAGUSD.a"),
    "GAS": ("GAS", "NAT.GAS", "NGAS", "NATGAS", "NG", "NGAS.cash"),
    "WTI": ("WTI", "USOIL", "USOil", "CL", "OIL", "CrudeOIL"),
    "BRENT": ("BRENT", "UKOIL", "UKOil", "BZ", "Brent"),
    "EURUSD": ("EURUSD", "EURUSD.", "EURUSDm", "EURUSD.a"),
    "GBPUSD": ("GBPUSD", "GBPUSD.", "GBPUSDm", "GBPUSD.a"),
    "USDJPY": ("USDJPY", "USDJPY.", "USDJPYm", "USDJPY.a"),
    "USDCHF": ("USDCHF", "USDCHF.", "USDCHFm", "USDCHF.a"),
    "USDCAD": ("USDCAD", "USDCAD.", "USDCADm", "USDCAD.a"),
    "AUDUSD": ("AUDUSD", "AUDUSD.", "AUDUSDm", "AUDUSD.a"),
    "NZDUSD": ("NZDUSD", "NZDUSD.", "NZDUSDm", "NZDUSD.a"),
    "BTCUSD": ("BTCUSD", "BTCUSDT", "BITCOIN", "BTCUSD.", "BTCUSDm", "BTCUSD.a"),
    "ETHUSD": ("ETHUSD", "ETHUSDT", "ETHEREUM", "ETHUSD.", "ETHUSDm", "ETHUSD.a"),
    "BNBUSD": ("BNBUSD", "BNBUSDT", "BINANCECOIN", "BNBUSD.", "BNBUSDm", "BNBUSD.a"),
    "SOLUSD": ("SOLUSD", "SOLUSDT", "SOLANA", "SOLUSD.", "SOLUSDm", "SOLUSD.a"),
    "XRPUSD": ("XRPUSD", "XRPUSDT", "RIPPLE", "XRPUSD.", "XRPUSDm", "XRPUSD.a"),
    "ADAUSD": ("ADAUSD", "ADAUSDT", "CARDANO", "ADAUSD.", "ADAUSDm", "ADAUSD.a"),
    "DOGEUSD": ("DOGEUSD", "DOGEUSDT", "DOGECOIN", "DOGEUSD.", "DOGEUSDm", "DOGEUSD.a"),
    "LTCUSD": ("LTCUSD", "LTCUSDT", "LITECOIN", "LTCUSD.", "LTCUSDm", "LTCUSD.a"),
    "BCHUSD": ("BCHUSD", "BCHUSDT", "BITCOINCASH", "BCHUSD.", "BCHUSDm", "BCHUSD.a"),
    "DOTUSD": ("DOTUSD", "DOTUSDT", "POLKADOT", "DOTUSD.", "DOTUSDm", "DOTUSD.a"),
    "LINKUSD": ("LINKUSD", "LINKUSDT", "CHAINLINK", "LINKUSD.", "LINKUSDm", "LINKUSD.a"),
    "AVAXUSD": ("AVAXUSD", "AVAXUSDT", "AVALANCHE", "AVAXUSD.", "AVAXUSDm", "AVAXUSD.a"),
    "MATICUSD": ("MATICUSD", "MATICUSDT", "POLYGON", "MATICUSD.", "MATICUSDm", "MATICUSD.a"),
    "POLUSD": ("POLUSD", "POLUSDT", "POLYGON", "POLUSD.", "POLUSDm", "POLUSD.a"),
    "TRXUSD": ("TRXUSD", "TRXUSDT", "TRON", "TRXUSD.", "TRXUSDm", "TRXUSD.a"),
    "UNIUSD": ("UNIUSD", "UNIUSDT", "UNISWAP", "UNIUSD.", "UNIUSDm", "UNIUSD.a"),
    "ATOMUSD": ("ATOMUSD", "ATOMUSDT", "COSMOS", "ATOMUSD.", "ATOMUSDm", "ATOMUSD.a"),
    "XLMUSD": ("XLMUSD", "XLMUSDT", "STELLAR", "XLMUSD.", "XLMUSDm", "XLMUSD.a"),
    "NEARUSD": ("NEARUSD", "NEARUSDT", "NEAR", "NEARUSD.", "NEARUSDm", "NEARUSD.a"),
    "APTUSD": ("APTUSD", "APTUSDT", "APTOS", "APTUSD.", "APTUSDm", "APTUSD.a"),
    "FILUSD": ("FILUSD", "FILUSDT", "FILECOIN", "FILUSD.", "FILUSDm", "FILUSD.a"),
}


def _asset_class(requested: str) -> str:
    for group, symbols in ASSET_GROUPS.items():
        if requested in symbols:
            return group
    return "OTHER"


def _fallback_match(requested: str, normalized: str) -> bool:
    rules = {
        "XAUUSD": ("xau", "gold"),
        "XAGUSD": ("xag", "silver"),
        "GAS": ("gas", "ngas", "natgas", "nat.gas"),
        "WTI": ("wti", "usoil", "crude", "oil"),
        "BRENT": ("brent", "ukoil"),
        "BTCUSD": ("btc", "bitcoin"),
        "ETHUSD": ("eth", "ethereum"),
        "BNBUSD": ("bnb", "binancecoin"),
        "SOLUSD": ("sol", "solana"),
        "XRPUSD": ("xrp", "ripple"),
        "ADAUSD": ("ada", "cardano"),
        "DOGEUSD": ("doge", "dogecoin"),
        "LTCUSD": ("ltc", "litecoin"),
        "BCHUSD": ("bch", "bitcoincash"),
        "DOTUSD": ("dot", "polkadot"),
        "LINKUSD": ("link", "chainlink"),
        "AVAXUSD": ("avax", "avalanche"),
        "MATICUSD": ("matic", "polygon"),
        "POLUSD": ("polygon", "matic"),
        "TRXUSD": ("trx", "tron"),
        "UNIUSD": ("uni", "uniswap"),
        "ATOMUSD": ("atom", "cosmos"),
        "XLMUSD": ("xlm", "stellar"),
        "NEARUSD": ("near",),
        "APTUSD": ("apt", "aptos"),
        "FILUSD": ("fil", "filecoin"),
    }
    return any(token.replace(".", "") in normalized for token in rules.get(requested, ()))


class MT5CockpitAdapter:
    """Build a normalized, read-only snapshot from the connected MT5 terminal."""

    def __init__(self, broker: MT5Broker | None = None):
        self.broker = broker or MT5Broker()

    def resolve_symbol(self, requested: str) -> str:
        requested = requested.upper()
        candidates = SYMBOL_ALIASES.get(requested, (requested,))
        self.broker.ensure_connected()

        for candidate in candidates:
            try:
                self.broker.symbol_info(candidate)
                return candidate
            except MT5ExecutionError:
                continue

        # Last resort: inspect the broker symbol universe for suffix/prefix names.
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:  # pragma: no cover - Windows deployment only
            raise MT5ExecutionError("MetaTrader5 package is unavailable.") from exc

        needle = requested.replace(".", "").lower()
        matches: list[str] = []
        for item in mt5.symbols_get() or ():
            name = str(item.name)
            normalized = name.replace(".", "").lower()
            if needle in normalized or _fallback_match(requested, normalized):
                matches.append(name)

        if matches:
            return matches[0]

        raise MT5ExecutionError(f"No MT5 symbol mapping found for {requested}")

    def snapshot(
        self,
        requested_symbols: tuple[str, ...] = DEFAULT_REQUESTED_SYMBOLS,
    ) -> dict[str, Any]:
        account = self.broker.connect()
        positions = self.broker.positions()
        prices: dict[str, float] = {}
        resolved: dict[str, str] = {}
        symbol_errors: dict[str, str] = {}
        rates: list[dict[str, Any]] = []

        for requested in requested_symbols:
            try:
                actual = self.resolve_symbol(requested)
                quote = self.broker.quote(actual)
                bid = float(quote["bid"])
                ask = float(quote["ask"])
                last = float(quote.get("last", 0.0) or 0.0)
                mid = last if last > 0 else (bid + ask) / 2.0
                spread = max(0.0, ask - bid)
                resolved[requested] = actual
                prices[requested] = mid
                rates.append({
                    "symbol": requested,
                    "broker_symbol": actual,
                    "asset_class": _asset_class(requested),
                    "bid": bid,
                    "ask": ask,
                    "last": last,
                    "mid": mid,
                    "spread": spread,
                })
            except MT5ExecutionError as exc:
                symbol_errors[requested] = str(exc)

        unrealized = sum(float(position["profit"]) for position in positions)
        server = str(account.get("server", ""))
        environment = "demo" if "demo" in server.lower() else "unknown"

        return {
            "status": "CONNECTED" if self.broker.connected else "OFFLINE",
            "mode": "mt5_read_only",
            "risk_profile": {
                "name": "ATLAS_MT5_EXECUTION_GATE",
                "default_risk_percent": 0.5,
                "max_risk_percent": 1.0,
                "max_position_percent": 15.0,
                "minimum_risk_reward": 1.5,
                "real_execution": (
                    "enabled"
                    if account.get("real_money_execution_enabled", False)
                    else "disabled"
                ),
            },
            "asset_groups": ASSET_GROUPS,
            "account": {
                "id": account["login"],
                "server": server,
                "balance": account["balance"],
                "currency": account["currency"],
            },
            "equity": {
                "balance": account["balance"],
                "equity": account["equity"],
                "unrealized_pnl": unrealized,
                "open_positions": len(positions),
                "positions": positions,
            },
            "prices": prices,
            "rates": rates,
            "resolved_symbols": resolved,
            "symbol_errors": symbol_errors,
            "broker": {
                "provider": "MetaTrader 5",
                "account_id": account["login"],
                "server": server,
                "environment": environment,
                "status": "connected",
                "trade_allowed": bool(account.get("trade_allowed", False)),
                "live_trading_enabled": not self.broker.config.dry_run,
                "real_money_execution_enabled": bool(
                    account.get("real_money_execution_enabled", False)
                ),
            },
        }
