from __future__ import annotations

import os
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.execution.provider_mode import mt5_connections_paused

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - package is Windows-only in deployment
    mt5 = None

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / ".env.local", override=False)

REAL_MONEY_ACK = "I_ACCEPT_REAL_MONEY_EXECUTION_RISK"


@dataclass(frozen=True)
class MT5Config:
    terminal_path: str | None = None
    login: int | None = None
    password: str | None = None
    server: str | None = None
    magic: int = 260830
    deviation: int = 20
    dry_run: bool = True
    demo_order_execution: bool = False
    real_money_execution: bool = False
    real_money_ack: str = ""

    @classmethod
    def from_env(cls) -> "MT5Config":
        login = os.getenv("MT5_LOGIN")
        return cls(
            terminal_path=os.getenv("MT5_TERMINAL_PATH"),
            login=int(login) if login else None,
            password=os.getenv("MT5_PASSWORD"),
            server=os.getenv("MT5_SERVER"),
            magic=int(os.getenv("MT5_MAGIC", "260830")),
            deviation=int(os.getenv("MT5_DEVIATION", "20")),
            dry_run=os.getenv("ATLAS_LIVE_TRADING", "false").lower() != "true",
            demo_order_execution=os.getenv("ATLAS_DEMO_ORDER_EXECUTION", "false").lower() == "true",
            real_money_execution=os.getenv("ATLAS_REAL_MONEY_EXECUTION", "false").lower() == "true",
            real_money_ack=os.getenv("ATLAS_REAL_MONEY_ACK", ""),
        )


class MT5ExecutionError(RuntimeError):
    pass


def account_type_name(raw_account: Any) -> str:
    return {0: "DEMO", 1: "CONTEST", 2: "REAL"}.get(
        int(getattr(raw_account, "trade_mode", -1)),
        "UNKNOWN",
    )


class MT5Broker:
    """ATLAS adapter for a locally running MetaTrader 5 terminal."""

    def __init__(self, config: MT5Config | None = None):
        self.config = config or MT5Config.from_env()
        self.connected = False

    def connect(self) -> dict[str, Any]:
        self._require_active_connection()
        if mt5 is None:
            raise MT5ExecutionError(
                "MetaTrader5 package is unavailable. Run ATLAS execution on Windows."
            )

        credentials = {}
        if self.config.login and self.config.password and self.config.server:
            credentials = {"login": self.config.login, "password": self.config.password, "server": self.config.server}
        initialized = (mt5.initialize(self.config.terminal_path, **credentials)
                       if self.config.terminal_path else mt5.initialize(**credentials))
        if not initialized:
            raise MT5ExecutionError(f"MT5 initialize failed: {mt5.last_error()}")

        account = mt5.account_info()
        if account is None:
            code = mt5.last_error()
            mt5.shutdown()
            raise MT5ExecutionError(f"MT5 account unavailable: {code}")

        self.connected = True
        account_type = account_type_name(account)
        return {
            "login": int(account.login),
            "server": str(account.server),
            "account_type": account_type,
            "balance": float(account.balance),
            "equity": float(account.equity),
            "currency": str(account.currency),
            "trade_allowed": bool(account.trade_allowed),
            "live_trading_enabled": not self.config.dry_run,
            "real_money_execution_enabled": (
                (not self.config.dry_run)
                and self.config.real_money_execution
                and self.config.real_money_ack == REAL_MONEY_ACK
                and account_type == "REAL"
                and bool(account.trade_allowed)
            ),
        }

    def disconnect(self) -> None:
        if mt5 is not None:
            mt5.shutdown()
        self.connected = False

    def _require_active_connection(self) -> None:
        if mt5_connections_paused():
            if self.connected:
                self.disconnect()
            raise MT5ExecutionError("MT5 connections are paused.")

    def ensure_connected(self) -> None:
        self._require_active_connection()
        if not self.connected:
            self.connect()

    def symbol_info(self, symbol: str) -> Any:
        self.ensure_connected()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise MT5ExecutionError(f"Unknown MT5 symbol: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise MT5ExecutionError(f"Could not select MT5 symbol: {symbol}")
        return mt5.symbol_info(symbol)

    def symbols(self) -> list[dict[str, Any]]:
        """Return normalized broker symbol metadata for universe discovery."""
        self.ensure_connected()
        raw = mt5.symbols_get()
        if raw is None:
            raise MT5ExecutionError(f"MT5 symbols unavailable: {mt5.last_error()}")

        items: list[dict[str, Any]] = []
        disabled = int(getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", 0))
        for info in raw:
            symbol = str(info.name)
            tick = mt5.symbol_info_tick(symbol)
            bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick is not None else 0.0
            ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick is not None else 0.0
            trade_mode = int(getattr(info, "trade_mode", disabled))
            items.append({
                "symbol": symbol,
                "description": str(getattr(info, "description", "")),
                "path": str(getattr(info, "path", "")),
                "visible": bool(getattr(info, "visible", False)),
                "tradeable": trade_mode != disabled,
                "trade_mode": trade_mode,
                "bid": bid,
                "ask": ask,
                "point": float(getattr(info, "point", 0.0) or 0.0),
                "digits": int(getattr(info, "digits", 0) or 0),
                "volume_min": float(getattr(info, "volume_min", 0.0) or 0.0),
                "volume_max": float(getattr(info, "volume_max", 0.0) or 0.0),
                "volume_step": float(getattr(info, "volume_step", 0.0) or 0.0),
                "trade_tick_value": float(getattr(info, "trade_tick_value", 0.0) or 0.0),
                "trade_tick_size": float(getattr(info, "trade_tick_size", 0.0) or 0.0),
                "contract_size": float(getattr(info, "trade_contract_size", 0.0) or 0.0),
            })
        return items

    def quote(self, symbol: str) -> dict[str, Any]:
        info = self.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5ExecutionError(f"No tick available for {symbol}")
        if info.point <= 0:
            raise MT5ExecutionError(f"Invalid point size for {symbol}")
        return {
            "symbol": symbol,
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "last": float(getattr(tick, "last", 0.0) or 0.0),
            "point": float(info.point),
            "digits": int(info.digits),
            "spread_points": float((tick.ask - tick.bid) / info.point),
        }

    def candles(self, symbol: str, timeframe: int, count: int = 200) -> list[dict[str, Any]]:
        if count < 1:
            raise MT5ExecutionError("Candle count must be positive.")
        self.symbol_info(symbol)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            raise MT5ExecutionError(f"No MT5 candle data for {symbol}: {mt5.last_error()}")
        return [{
            "open_time": int(row["time"] * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["tick_volume"]),
            "close_time": int(row["time"] * 1000),
        } for row in rates]

    def positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        self.ensure_connected()
        raw = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if raw is None:
            return []
        return [{
            "ticket": int(p.ticket),
            "symbol": str(p.symbol),
            "direction": "LONG" if p.type == mt5.POSITION_TYPE_BUY else "SHORT",
            "volume": float(p.volume),
            "price_open": float(p.price_open),
            "sl": float(p.sl),
            "tp": float(p.tp),
            "profit": float(p.profit),
            "magic": int(p.magic),
        } for p in raw]

    def pending_orders(self) -> list[dict[str, Any]]:
        self.ensure_connected()
        raw = mt5.orders_get()
        if raw is None:
            return []
        items: list[dict[str, Any]] = []
        for order in raw:
            order_type = int(getattr(order, "type", -1))
            direction = "BUY" if order_type in {int(getattr(mt5, "ORDER_TYPE_BUY", 0)), int(getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2)), int(getattr(mt5, "ORDER_TYPE_BUY_STOP", 4))} else "SELL"
            items.append({
                "ticket": int(getattr(order, "ticket", 0) or 0),
                "symbol": str(getattr(order, "symbol", "") or ""),
                "direction": direction,
                "volume": float(getattr(order, "volume_initial", 0.0) or 0.0),
                "price_open": float(getattr(order, "price_open", 0.0) or 0.0),
                "sl": float(getattr(order, "sl", 0.0) or 0.0),
                "tp": float(getattr(order, "tp", 0.0) or 0.0),
                "time": int(getattr(order, "time_setup", 0) or 0),
            })
        return items

    def recent_deals(self, days: int = 7) -> list[dict[str, Any]]:
        self.ensure_connected()
        end = datetime.now(UTC)
        start = end - timedelta(days=max(1, days))
        raw = mt5.history_deals_get(start, end) or ()
        exit_code = int(getattr(mt5, "DEAL_ENTRY_OUT", 1))
        items: list[dict[str, Any]] = []
        for deal in raw:
            if int(getattr(deal, "entry", -1)) != exit_code:
                continue
            deal_type = int(getattr(deal, "type", -1))
            direction = "BUY" if deal_type == int(getattr(mt5, "DEAL_TYPE_BUY", 0)) else "SELL"
            items.append({
                "ticket": int(getattr(deal, "ticket", 0) or 0),
                "position_id": int(getattr(deal, "position_id", 0) or 0),
                "symbol": str(getattr(deal, "symbol", "") or ""),
                "direction": direction,
                "volume": float(getattr(deal, "volume", 0.0) or 0.0),
                "price": float(getattr(deal, "price", 0.0) or 0.0),
                "profit": float(getattr(deal, "profit", 0.0) or 0.0),
                "time": int(getattr(deal, "time", 0) or 0),
            })
        return sorted(items, key=lambda item: item["time"], reverse=True)[:50]

    def _normalized_volume(self, symbol: str, volume: float) -> float:
        if volume <= 0:
            raise MT5ExecutionError("Order volume must be greater than zero.")
        info = self.symbol_info(symbol)
        minimum = float(info.volume_min)
        maximum = float(info.volume_max)
        step = float(info.volume_step)
        if step <= 0 or maximum < minimum:
            raise MT5ExecutionError(f"Invalid volume constraints for {symbol}")
        if volume < minimum or volume > maximum:
            raise MT5ExecutionError(f"Order volume outside broker limits for {symbol}.")
        steps = round((volume - minimum) / step)
        normalized = minimum + steps * step
        if abs(normalized - volume) > 1e-8:
            raise MT5ExecutionError(f"Order volume must match broker step for {symbol}.")
        return round(normalized, 8)

    def _filling_type(self, info: Any) -> int:
        mode = getattr(info, "filling_mode", None)
        for candidate_name in ("ORDER_FILLING_FOK", "ORDER_FILLING_IOC", "ORDER_FILLING_RETURN"):
            candidate = getattr(mt5, candidate_name, None)
            if candidate is not None and mode == candidate:
                return int(candidate)
        return int(getattr(mt5, "ORDER_FILLING_IOC", 1))

    def market_order(self, symbol: str, direction: str, volume: float, stop_loss: float, take_profit: float, comment: str = "ATLAS", *, expected_account_type: str | None = None, expected_login: int | None = None) -> dict[str, Any]:
        self.ensure_connected()
        direction = direction.upper()
        if direction not in {"LONG", "SHORT", "BUY", "SELL"}:
            raise MT5ExecutionError(f"Unsupported direction: {direction}")
        side = "BUY" if direction in {"LONG", "BUY"} else "SELL"
        info = self.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5ExecutionError(f"No tick available for {symbol}")
        price = float(tick.ask if side == "BUY" else tick.bid)
        volume = self._normalized_volume(symbol, volume)
        digits = int(info.digits)
        price = round(price, digits)
        stop_loss = round(float(stop_loss), digits)
        take_profit = round(float(take_profit), digits)
        if side == "BUY" and not (stop_loss < price < take_profit):
            raise MT5ExecutionError("BUY requires SL < entry < TP.")
        if side == "SELL" and not (take_profit < price < stop_loss):
            raise MT5ExecutionError("SELL requires TP < entry < SL.")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": self.config.deviation,
            "magic": self.config.magic,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_type(info),
        }
        if self.config.dry_run:
            return {"status": "DRY_RUN", "symbol": symbol, "side": side, "volume": volume, "price": price, "sl": stop_loss, "tp": take_profit}

        account = mt5.account_info()
        if account is None or not bool(account.trade_allowed):
            raise MT5ExecutionError("MT5 account does not allow trading.")
        account_type = account_type_name(account)
        if expected_account_type and account_type != expected_account_type:
            raise MT5ExecutionError("MT5 account mode changed before order submission.")
        if expected_login is not None and int(account.login) != int(expected_login):
            raise MT5ExecutionError("MT5 account login changed before order submission.")
        if account_type == "DEMO":
            if not self.config.demo_order_execution:
                raise MT5ExecutionError("Demo broker order execution is disabled.")
        elif account_type == "REAL":
            if not self.config.real_money_execution or self.config.real_money_ack != REAL_MONEY_ACK:
                raise MT5ExecutionError("Real-money execution is disabled.")
        else:
            raise MT5ExecutionError("Unsupported MT5 account mode.")
        projected = mt5.order_calc_profit(request["type"], symbol, volume, price, stop_loss)
        equity = float(getattr(account, "equity", 0.0) or 0.0)
        if projected is None or not math.isfinite(float(projected)) or equity <= 0:
            raise MT5ExecutionError("Unable to calculate stop-loss risk.")
        if projected >= 0 or abs(float(projected)) > equity * 0.01:
            raise MT5ExecutionError("Order stop-loss risk exceeds 1% of account equity.")
        check = mt5.order_check(request)
        if check is None or check.retcode != 0:
            raise MT5ExecutionError("MT5 order check rejected the request.")
        result = mt5.order_send(request)
        if result is None:
            raise MT5ExecutionError(f"MT5 order_send returned None: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise MT5ExecutionError(f"MT5 order rejected: retcode={result.retcode}, comment={result.comment}")
        return {"status": "FILLED", "ticket": int(result.order), "deal": int(result.deal), "symbol": symbol, "side": side, "volume": float(result.volume), "price": float(result.price), "sl": stop_loss, "tp": take_profit, "comment": str(result.comment)}

    def close_position(self, ticket: int) -> dict[str, Any]:
        self.ensure_connected()
        raw = mt5.positions_get(ticket=ticket)
        if not raw:
            raise MT5ExecutionError(f"Position not found: {ticket}")
        position = raw[0]
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise MT5ExecutionError(f"No quote for {position.symbol}")
        info = mt5.symbol_info(position.symbol)
        if info is None:
            raise MT5ExecutionError(f"Unknown symbol: {position.symbol}")
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = float(tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask)
        price = round(price, int(info.digits))
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": close_type,
            "position": int(position.ticket),
            "price": price,
            "deviation": self.config.deviation,
            "magic": self.config.magic,
            "comment": "ATLAS-CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_type(info),
        }
        if self.config.dry_run:
            return {"status": "DRY_RUN_CLOSE", "ticket": ticket, "symbol": position.symbol, "price": price}
        account = mt5.account_info()
        if account is None or not bool(account.trade_allowed):
            raise MT5ExecutionError("MT5 account does not allow trading.")
        account_type = account_type_name(account)
        if account_type == "DEMO" and not self.config.demo_order_execution:
            raise MT5ExecutionError("Demo broker order execution is disabled.")
        if account_type == "REAL" and (
            not self.config.real_money_execution or self.config.real_money_ack != REAL_MONEY_ACK
        ):
            raise MT5ExecutionError("Real-money execution is disabled.")
        if account_type not in {"DEMO", "REAL"}:
            raise MT5ExecutionError("Unsupported MT5 account mode.")
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            detail = mt5.last_error() if result is None else f"{result.retcode}: {result.comment}"
            raise MT5ExecutionError(f"MT5 close rejected: {detail}")
        return {"status": "CLOSED", "ticket": ticket, "deal": int(result.deal), "price": float(result.price)}
