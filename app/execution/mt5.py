from __future__ import annotations

import os
import math
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
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
    use_active_session: bool = False

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
            use_active_session=os.getenv("MT5_USE_ACTIVE_SESSION", "false").lower() == "true",
        )


class MT5ExecutionError(RuntimeError):
    pass


class MT5Broker:
    """ATLAS adapter for a locally running MetaTrader 5 terminal."""

    def __init__(self, config: MT5Config | None = None):
        self.config = config or MT5Config.from_env()
        self.connected = False
        self._connected_account = None

    def connect(self) -> dict[str, Any]:
        if mt5 is None:
            raise MT5ExecutionError(
                "MetaTrader5 package is unavailable. Run ATLAS execution on Windows."
            )

        initialized = mt5.initialize(self.config.terminal_path) if self.config.terminal_path else mt5.initialize()
        if not initialized:
            raise MT5ExecutionError(f"MT5 initialize failed: {mt5.last_error()}")

        if (not self.config.use_active_session
                and self.config.login and self.config.password and self.config.server):
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
                    or (not self.config.use_active_session and self.config.login and int(account.login) != self.config.login)
                    or (not self.config.use_active_session and self.config.server and account.server != self.config.server)):
                mt5.shutdown()
                raise MT5ExecutionError("Configured demo account is not the active MT5 session.")

        self._connected_account = self.account_identity(account)
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

    @staticmethod
    def account_identity(account) -> dict:
        try:
            def value(name):
                return account[name] if isinstance(account, dict) else getattr(account, name)
            login, server, mode = int(value("login")), str(value("server")), int(value("trade_mode"))
            if login <= 0 or not server.strip() or mode not in {0, 1, 2}:
                raise ValueError()
            return {"login": login, "server": server, "trade_mode": mode}
        except (KeyError, AttributeError, TypeError, ValueError):
            raise MT5ExecutionError("Account identity is missing or invalid.") from None

    def _validate_account(self, expected):
        current = mt5.account_info()
        if current is None or self.account_identity(current) != self.account_identity(expected):
            raise MT5ExecutionError("Target account changed before submission.")
        if os.getenv("MT5_REQUIRE_DEMO", "false").lower() == "true" and current.trade_mode != 0:
            raise MT5ExecutionError("Target account is not a demo account.")
        return current

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
            raise MT5ExecutionError(f"MT5 positions unavailable: {mt5.last_error()}")
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

    @staticmethod
    def _positive(value: float, name: str) -> float:
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise MT5ExecutionError(f"{name} must be finite and positive.")
        return value

    def cash_risk(self, symbol: str, entry: float, stop_loss: float, volume: float) -> float:
        entry = self._positive(entry, "Entry")
        stop_loss = self._positive(stop_loss, "Stop loss")
        volume = self._positive(volume, "Volume")
        side = mt5.ORDER_TYPE_BUY if stop_loss < entry else mt5.ORDER_TYPE_SELL
        loss = mt5.order_calc_profit(side, symbol, volume, entry, stop_loss)
        if loss is None or not math.isfinite(float(loss)):
            raise MT5ExecutionError(f"Cash risk unavailable for {symbol}")
        return max(0.0, -float(loss))

    @staticmethod
    def _require_fresh_quote(quote: dict[str, Any]) -> None:
        timestamp = float(quote.get("time_msc", 0)) / 1000 or float(quote.get("time", 0))
        max_age = float(os.getenv("ATLAS_MT5_MAX_QUOTE_AGE_SECONDS", "30"))
        age = time.time() - timestamp
        if not math.isfinite(timestamp) or not math.isfinite(max_age) or max_age <= 0 or age < -5 or age > max_age:
            raise MT5ExecutionError("MT5 quote is missing, stale or has an invalid timestamp.")

    def risk_snapshot(self) -> dict[str, Any]:
        """Read current account-wide risk and today's UTC realized trading P&L."""
        self.ensure_connected()
        collected_at = time.time()
        account = mt5.account_info()
        if account is None:
            raise MT5ExecutionError("MT5 account risk state unavailable.")
        equity = self._positive(account.equity, "Account equity")
        balance = float(account.balance)
        identity = self.account_identity(account)
        credit = float(getattr(account, "credit", 0.0))
        if not math.isfinite(balance) or not math.isfinite(credit):
            raise MT5ExecutionError("Invalid account balance/credit.")
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(start, now)
        positions = mt5.positions_get()
        if deals is None or positions is None:
            raise MT5ExecutionError("MT5 portfolio/history unavailable; execution refused.")
        trading_types = {mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL}
        for name in ("DEAL_TYPE_CHARGE", "DEAL_TYPE_COMMISSION", "DEAL_TYPE_COMMISSION_DAILY",
                     "DEAL_TYPE_COMMISSION_MONTHLY", "DEAL_TYPE_COMMISSION_AGENT_DAILY",
                     "DEAL_TYPE_COMMISSION_AGENT_MONTHLY"):
            if hasattr(mt5, name):
                trading_types.add(getattr(mt5, name))
        pnl = 0.0
        balance_change = 0.0
        credit_type = getattr(mt5, "DEAL_TYPE_CREDIT", 3)
        for deal in deals:
            values = [float(getattr(deal, name, 0.0)) for name in ("profit", "commission", "swap", "fee")]
            if not all(math.isfinite(v) for v in values):
                raise MT5ExecutionError("Non-finite account deal amounts.")
            amount = sum(values)
            if deal.type in trading_types:
                pnl += amount
            # Credit changes account.credit, not account.balance. Undo every other
            # intraday balance flow, including deposits, withdrawals and trading costs.
            if deal.type != credit_type:
                balance_change += amount
        daily_start_capital = self._positive(balance - balance_change, "Start-of-day capital")
        open_cash_risk = 0.0
        symbols = []
        for position in positions:
            stop = self._positive(position.sl, "Position stop loss")
            quote = self.quote(position.symbol)
            self._require_fresh_quote(quote)
            side = mt5.ORDER_TYPE_BUY if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_SELL
            entry = self._positive(quote["bid"] if side == mt5.ORDER_TYPE_BUY else quote["ask"], "Position quote")
            self._positive(position.volume, "Position volume")
            loss = mt5.order_calc_profit(side, position.symbol, position.volume, entry, stop)
            if loss is None or not math.isfinite(float(loss)):
                raise MT5ExecutionError("Open position cash risk unavailable.")
            open_cash_risk += max(0.0, -float(loss))
            symbols.append({"symbol": str(position.symbol)})
        # Bracket the history/positions reads. A closing deal or cash flow
        # during collection would mix account balances from different instants.
        latest = mt5.account_info()
        if latest is None or self.account_identity(latest) != identity or float(latest.balance) != balance or float(getattr(latest, "credit", 0.0)) != credit:
            raise MT5ExecutionError("Account balance, credit or identity changed during risk collection.")
        return {**identity, "equity": equity, "daily_realized_pnl": pnl,
                "daily_start_capital": daily_start_capital,
                "open_risk_percent": open_cash_risk / equity * 100.0,
                "positions": symbols, "timestamp": collected_at}

    def volume_for_risk(self, symbol: str, entry: float, stop_loss: float, risk_amount: float) -> float:
        self.ensure_connected()
        risk_amount = self._positive(risk_amount, "Risk amount")
        info = self.symbol_info(symbol)
        reference = self._positive(info.volume_min, "Minimum volume")
        reference_loss = self.cash_risk(symbol, entry, stop_loss, reference)
        if reference_loss <= 0:
            raise MT5ExecutionError("Invalid cash risk per lot.")
        raw_volume = round(reference * risk_amount / reference_loss, 12)
        volume = self._normalized_volume(symbol, raw_volume)
        if self.cash_risk(symbol, entry, stop_loss, volume) > risk_amount + 1e-8:
            raise MT5ExecutionError("Normalized volume exceeds cash-risk budget.")
        return volume

    def _normalized_volume(self, symbol: str, volume: float) -> float:
        volume = self._positive(volume, "Order volume")
        info = self.symbol_info(symbol)
        minimum = self._positive(info.volume_min, "Minimum volume")
        maximum = self._positive(info.volume_max, "Maximum volume")
        step = self._positive(info.volume_step, "Volume step")
        if maximum < minimum or volume < minimum:
            raise MT5ExecutionError(f"Requested volume is below broker minimum or constraints invalid for {symbol}")
        value = Decimal(str(min(volume, maximum)))
        increment = Decimal(str(step))
        normalized = (value / increment).to_integral_value(rounding=ROUND_FLOOR) * increment
        if normalized < Decimal(str(minimum)):
            raise MT5ExecutionError("Risk budget cannot support the broker minimum.")
        return float(normalized)

    def _filling_type(self, info: Any) -> int:
        mode = getattr(info, "filling_mode", None)
        for candidate_name in ("ORDER_FILLING_FOK", "ORDER_FILLING_IOC", "ORDER_FILLING_RETURN"):
            candidate = getattr(mt5, candidate_name, None)
            if candidate is not None and mode == candidate:
                return int(candidate)
        return int(getattr(mt5, "ORDER_FILLING_IOC", 1))

    def market_order(self, symbol: str, direction: str, volume: float, stop_loss: float, take_profit: float, comment: str = "ATLAS", *, max_cash_risk: float | None = None, expected_entry: float | None = None, max_entry_deviation: float | None = None, expected_account: dict | None = None) -> dict[str, Any]:
        self.ensure_connected()
        direction = direction.upper()
        if direction not in {"LONG", "SHORT", "BUY", "SELL"}:
            raise MT5ExecutionError(f"Unsupported direction: {direction}")
        side = "BUY" if direction in {"LONG", "BUY"} else "SELL"
        info = self.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5ExecutionError(f"No tick available for {symbol}")
        if max_cash_risk is not None or expected_entry is not None:
            self._require_fresh_quote({"time": getattr(tick, "time", 0), "time_msc": getattr(tick, "time_msc", 0)})
        price = self._positive(tick.ask if side == "BUY" else tick.bid, "Final price")
        volume = self._normalized_volume(symbol, volume)
        digits = int(info.digits)
        price = round(price, digits)
        stop_loss = round(self._positive(stop_loss, "Stop loss"), digits)
        take_profit = round(self._positive(take_profit, "Take profit"), digits)
        if side == "BUY" and not (stop_loss < price < take_profit):
            raise MT5ExecutionError("BUY requires SL < entry < TP.")
        if side == "SELL" and not (take_profit < price < stop_loss):
            raise MT5ExecutionError("SELL requires TP < entry < SL.")

        if expected_entry is not None:
            reference = self._positive(expected_entry, "Expected entry")
            limit = self._positive(max_entry_deviation, "Maximum entry deviation")
            if abs(price - reference) > limit + 1e-12:
                raise MT5ExecutionError("Final quote exceeds allowed entry drift.")
        if max_cash_risk is not None:
            reward_risk = abs(take_profit - price) / abs(price - stop_loss)
            if reward_risk < 1.5 and not math.isclose(reward_risk, 1.5, rel_tol=0, abs_tol=1e-12):
                raise MT5ExecutionError("Final rounded quote violates minimum 1.5 reward/risk.")
            budget = self._positive(max_cash_risk, "Cash-risk budget")
            if self.cash_risk(symbol, price, stop_loss, volume) > budget + 1e-8:
                raise MT5ExecutionError("Final quote exceeds approved cash-risk budget.")

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
        target = expected_account or self._connected_account
        if target is not None:
            self._validate_account(target)
        if self.config.dry_run:
            return {"status": "DRY_RUN", "symbol": symbol, "side": side, "volume": volume, "price": price, "sl": stop_loss, "tp": take_profit}

        account = self._validate_account(target) if target is not None else mt5.account_info()
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

