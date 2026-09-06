"""Read-only MT5 state for the Trader Cockpit.

This adapter exposes account, position, and quote state only. It never places
or closes orders. Live execution remains controlled separately by
ATLAS_LIVE_TRADING and the execution gateway.
"""
from __future__ import annotations

from typing import Any

from app.execution.mt5 import MT5Broker, MT5ExecutionError


SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "XAUUSD": ("XAUUSD", "GOLD", "XAUUSD.", "XAUUSDm", "XAUUSD.a"),
    "XAGUSD": ("XAGUSD", "SILVER", "XAGUSD.", "XAGUSDm", "XAGUSD.a"),
    "EURUSD": ("EURUSD", "EURUSD.", "EURUSDm", "EURUSD.a"),
    "GBPUSD": ("GBPUSD", "GBPUSD.", "GBPUSDm", "GBPUSD.a"),
}


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
            if needle in normalized or (
                requested == "XAUUSD" and ("xau" in normalized or "gold" in normalized)
            ) or (
                requested == "XAGUSD" and ("xag" in normalized or "silver" in normalized)
            ):
                matches.append(name)

        if matches:
            return matches[0]

        raise MT5ExecutionError(f"No MT5 symbol mapping found for {requested}")

    def snapshot(
        self,
        requested_symbols: tuple[str, ...] = ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD"),
    ) -> dict[str, Any]:
        account = self.broker.connect()
        positions = self.broker.positions()
        prices: dict[str, float] = {}
        resolved: dict[str, str] = {}
        symbol_errors: dict[str, str] = {}

        for requested in requested_symbols:
            try:
                actual = self.resolve_symbol(requested)
                quote = self.broker.quote(actual)
                bid = float(quote["bid"])
                ask = float(quote["ask"])
                last = float(quote.get("last", 0.0) or 0.0)
                resolved[requested] = actual
                prices[requested] = last if last > 0 else (bid + ask) / 2.0
            except MT5ExecutionError as exc:
                symbol_errors[requested] = str(exc)

        unrealized = sum(float(position["profit"]) for position in positions)
        server = str(account.get("server", ""))
        environment = "demo" if "demo" in server.lower() else "unknown"

        return {
            "status": "CONNECTED" if self.broker.connected else "OFFLINE",
            "mode": "mt5_read_only",
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
            },
        }
