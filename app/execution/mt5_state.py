"""Read-only MT5 state for the Trader Cockpit.

This adapter intentionally exposes account/positions/quotes only. It never
places or closes orders, so the cockpit can safely connect to an MT5 demo
terminal while live execution remains disabled.
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

        # Last resort: inspect the terminal's visible/known symbol universe.
        import MetaTrader5 as mt5

        needle = requested.replace(".", "").lower()
        matches = []
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

    def snapshot(self, requested_symbols: tuple[str, ...] = ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD")) -> dict[str, Any]:
        account = self.broker.connect()
        positions = self.broker.positions()
        prices: dict[str, float] = {}
        resolved: dict[str, str] = {}
        symbol_errors: dict[str, str] = {}

        for requested in requested_symbols:
            try:
                actual = self.resolve_symbol(requested)
                quote = self.broker.quote(actual)
                resolved[requested] = actual
                prices[requested] = quote["last"] or ((quote["bid"] + quote["ask"]) / 2.0)
            except MT5ExecutionError as exc:
                symbol_errors[requested] = str(exc)

        unrealized = sum(float(position["profit"]) for position in positions)
        return {
            "status": "LIVE" if self.broker.connected else "OFFLINE",
            "mode": "mt5_demo_read_only" if self.broker.config.dry_run else "mt5_execution_disabled",
            "account": {
                "id": account["login"],
                "server": account["server"],
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
                "server": account["server"],
                "environment": "demo" if account["server"] else "paper",
                "status": "connected",
                "trade_allowed": account["trade_allowed"],
                "live_trading_enabled": False,
            },
        }
