from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - package is Windows-only in deployment
    mt5 = None


@dataclass(frozen=True)
class MT5Config:
    terminal_path: str | None = None
    login: int | None = None
    password: str | None = None
    server: str | None = None
    magic: int = 260830
    deviation: int = 20
    dry_run: bool = True

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
        )


class MT5ExecutionError(RuntimeError):
    pass


class MT5Broker:
    """ATLAS adapter for a locally running MetaTrader 5 terminal."""

    def __init__(self, config: MT5Config | None = None):
        self.config = config or MT5Config.from_env()
        self.connected = False

    def connect(self) -> dict[str, Any]:
        if mt5 is None:
            raise MT5ExecutionError(
                "MetaTrader5 package is unavailable. Run ATLAS execution on Windows."
            )

        initialized = mt5.initialize(self.config.terminal_path) if self.config.terminal_path else mt5.initialize()
        if not initialized:
            raise MT5ExecutionError(f"MT5 initialize failed: {mt5.last_error()}")

        if self.config.login and self.config.password and self.config.server:
            if not mt5.login(self.config.login, password=self.config.password, server=self.config.server):
                code = mt5.last_error()
                mt5.shutdown()
                raise MT5ExecutionError(f"MT5 login failed: {code}")

        account = mt5.account_info()
        if account is None:
            code = mt5.last_error()
            mt5.shutdown()
            raise MT5ExecutionError(f"MT5 account unavailable: {code}")

        if os.getenv("MT5_REQUIRE_DEMO", "false").lower() == "true":
            if (getattr(account, "trade_mode", None) != mt5.ACCOUNT_TRADE_MODE_DEMO
                    or (self.config.login and int(account.login) != self.config.login)
                    or (self.config.server and account.server != self.config.server)):
                mt5.shutdown()
                raise MT5ExecutionError("Configured demo account is not the active MT5 session.")

        self.connected = True
        return {
            "login": int(account.login),
            "server": str(account.server),
            "balance": float(account.balance),
            "equity": float(account.equity),
            "currency": str(account.currency),
            "trade_allowed": bool(account.trade_allowed),
            "trade_mode": int(account.trade_mode),
            "live_trading_enabled": not self.config.dry_run,
        }

    def disconnect(self) -> None:
        if mt5 is not None:
            mt5.shutdown()
        self.connected = False

    def ensure_connected(self) -> None:
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
            "time": int(getattr(tick, "time", 0) or 0),
            "time_msc": int(getattr(tick, "time_msc", 0) or 0),
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

    def volume_for_risk(self, symbol: str, entry: float, stop_loss: float, risk_amount: float) -> float:
        """Convert a cash-risk budget into MT5 lot volume using symbol tick metadata."""
        if entry <= 0 or stop_loss <= 0 or risk_amount <= 0:
            raise MT5ExecutionError("Entry, stop loss, and risk amount must be greater than zero.")
        info = self.symbol_info(symbol)
        tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
        tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
        if tick_size <= 0 or tick_value <= 0:
            raise MT5ExecutionError(f"Risk sizing metadata unavailable for {symbol}")
        distance = abs(float(entry) - float(stop_loss))
        ticks_at_risk = distance / tick_size
        cash_risk_per_lot = ticks_at_risk * tick_value
        if cash_risk_per_lot <= 0:
            raise MT5ExecutionError(f"Invalid cash risk per lot for {symbol}")
        raw_volume = float(risk_amount) / cash_risk_per_lot
        return self._normalized_volume(symbol, raw_volume)

    def _normalized_volume(self, symbol: str, volume: float) -> float:
        if volume <= 0:
            raise MT5ExecutionError("Order volume must be greater than zero.")
        info = self.symbol_info(symbol)
        minimum = float(info.volume_min)
        maximum = float(info.volume_max)
        step = float(info.volume_step)
        if step <= 0 or maximum < minimum:
            raise MT5ExecutionError(f"Invalid volume constraints for {symbol}")
        volume = min(max(volume, minimum), maximum)
        steps = int(volume / step)
        normalized = steps * step
        if normalized < minimum:
            normalized = minimum
        return round(normalized, 8)

    def _filling_type(self, info: Any) -> int:
        mode = getattr(info, "filling_mode", None)
        for candidate_name in ("ORDER_FILLING_FOK", "ORDER_FILLING_IOC", "ORDER_FILLING_RETURN"):
            candidate = getattr(mt5, candidate_name, None)
            if candidate is not None and mode == candidate:
                return int(candidate)
        return int(getattr(mt5, "ORDER_FILLING_IOC", 1))

    def market_order(self, symbol: str, direction: str, volume: float, stop_loss: float, take_profit: float, comment: str = "ATLAS") -> dict[str, Any]:
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
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            detail = mt5.last_error() if result is None else f"{result.retcode}: {result.comment}"
            raise MT5ExecutionError(f"MT5 close rejected: {detail}")
        return {"status": "CLOSED", "ticket": ticket, "deal": int(result.deal), "price": float(result.price)}
