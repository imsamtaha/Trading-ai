from __future__ import annotations

import os
import threading
from copy import deepcopy
from typing import Any, Callable

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError, REAL_MONEY_ACK
from app.mt5_demo.audit import TradeAudit
from app.strategy.universe import build_universe
from app.runtime_control.service import get_demo_execution_enabled

_MT5_TERMINAL_LOCK = threading.RLock()


class MT5DemoError(RuntimeError):
    pass


class MT5DemoService:
    def __init__(self, repository: Any, broker_factory: Callable[[dict[str, Any]], Any] | None = None,
                 execution_factory: Callable[[dict[str, Any]], Any] | None = None,
                 demo_orders_enabled: bool | None = None, real_orders_enabled: bool | None = None,
                 audit_store: TradeAudit | None = None) -> None:
        self.repository = repository
        self.broker_factory = broker_factory or self._default_broker_factory
        self._demo_runtime_managed = demo_orders_enabled is None
        self.demo_orders_enabled = get_demo_execution_enabled() if demo_orders_enabled is None else bool(demo_orders_enabled)
        self.real_orders_enabled = ((os.getenv("ATLAS_USER_REAL_ORDERS", "false").lower() == "true")
                                    and os.getenv("ATLAS_REAL_MONEY_ACK", "") == REAL_MONEY_ACK) if real_orders_enabled is None else real_orders_enabled
        self.execution_factory = execution_factory or self._execution_broker_factory
        self._sessions: dict[str, dict[str, Any]] = {}
        self._active_real: dict[str, int] = {}
        self.audit = audit_store or TradeAudit()

    @staticmethod
    def _default_broker_factory(credentials: dict[str, Any]) -> MT5Broker:
        if credentials.get("attach_current"):
            return MT5Broker(MT5Config(
                terminal_path=os.getenv("MT5_TERMINAL_PATH"),
                dry_run=True,
                real_money_execution=False,
            ))
        return MT5Broker(MT5Config(
            terminal_path=os.getenv("MT5_TERMINAL_PATH"),
            login=int(credentials["login"]),
            password=str(credentials["password"]),
            server=str(credentials["server"]),
            dry_run=True,
            real_money_execution=False,
        ))

    def _execution_broker_factory(self, credentials: dict[str, Any]) -> MT5Broker:
        return MT5Broker(MT5Config(
            terminal_path=os.getenv("MT5_TERMINAL_PATH"),
            login=int(credentials["login"]), password=str(credentials["password"]),
            server=str(credentials["server"]), dry_run=False,
            demo_order_execution=self.demo_orders_enabled,
            real_money_execution=self.real_orders_enabled,
            real_money_ack=os.getenv("ATLAS_REAL_MONEY_ACK", ""),
        ))

    @staticmethod
    def _mask_login(login: int | str) -> str:
        token = str(login)
        return f"***{token[-4:]}" if token else "***"

    def connect_demo(self, user_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
        return self.connect_account(user_id, credentials, "DEMO")

    def attach_current_demo(self, user_id: str) -> dict[str, Any]:
        broker = self.broker_factory({"attach_current": True})
        with _MT5_TERMINAL_LOCK:
            try:
                account = broker.connect()
                if str(account.get("account_type", "UNKNOWN")).upper() != "DEMO":
                    raise MT5DemoError("Current MT5 terminal must be a Demo account.")
                metadata = {
                    "account_masked": self._mask_login(account.get("login")),
                    "account_type": "DEMO",
                    "server": str(account.get("server", "")),
                    "broker": "FxPro",
                    "connection_state": "CONNECTED",
                }
                self.repository.set_mt5_connection(user_id, metadata)
                self._sessions[user_id] = {
                    "login": int(account["login"]),
                    "server": str(account.get("server", "")),
                    "broker": "FxPro",
                    "account_type": "DEMO",
                    "attach_current": True,
                }
                return {**metadata, "connected": True, "read_only": True}
            except MT5ExecutionError as exc:
                raise MT5DemoError("Unable to attach current MT5 Demo account.") from exc
            finally:
                try:
                    broker.disconnect()
                except Exception:
                    pass

    def connect_account(self, user_id: str, credentials: dict[str, Any], expected_type: str) -> dict[str, Any]:
        if expected_type not in {"DEMO", "REAL"}:
            raise MT5DemoError("Unsupported MT5 account mode.")
        self._active_real.pop(user_id, None)
        broker = self.broker_factory(credentials)
        _MT5_TERMINAL_LOCK.acquire()
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                account_type = str(account.get("account_type", "UNKNOWN")).upper()
                if account_type != expected_type:
                    raise MT5DemoError(f"MT5 account must be {expected_type}.")
            metadata = {
                "account_masked": self._mask_login(account.get("login", credentials.get("login"))),
                "account_type": expected_type,
                "server": str(account.get("server", credentials.get("server", ""))),
                "broker": str(credentials.get("broker", "FxPro")),
                "connection_state": "CONNECTED",
            }
            self.repository.set_mt5_connection(user_id, metadata)
            self._sessions[user_id] = {
                "login": int(credentials["login"]),
                "password": str(credentials["password"]),
                "server": str(credentials["server"]),
                "broker": str(credentials.get("broker", "FxPro")),
                "account_type": expected_type,
            }
            return {**metadata, "connected": True, "real_money_execution_enabled": False}
        except MT5DemoError:
            raise
        except (MT5ExecutionError, KeyError, TypeError, ValueError) as exc:
            raise MT5DemoError("Unable to connect to MT5 Demo account.") from exc
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass
            finally:
                _MT5_TERMINAL_LOCK.release()

    def disconnect_demo(self, user_id: str) -> dict[str, Any]:
        self._active_real.pop(user_id, None)
        self._sessions.pop(user_id, None)
        clear = getattr(self.repository, "clear_mt5_connection", None)
        if callable(clear):
            clear(user_id)
        return {"connected": False}

    def get_demo_state(self, user_id: str) -> dict[str, Any]:
        credentials = self._sessions.get(user_id)
        if credentials is None:
            metadata = self.repository.get_mt5_connection(user_id)
            return {
                "connected": False,
                "account_masked": metadata.get("account_masked") if metadata else None,
                "account_type": metadata.get("account_type") if metadata else None,
                "server": metadata.get("server") if metadata else None,
                "broker": metadata.get("broker") if metadata else None,
            }
        broker = self.broker_factory(credentials)
        _MT5_TERMINAL_LOCK.acquire()
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                account_type = str(account.get("account_type", "UNKNOWN")).upper()
                if account_type != credentials["account_type"]:
                    self._sessions.pop(user_id, None)
                    raise MT5DemoError("MT5 account mode changed.")
                return {
                    "connected": True,
                    "account_masked": self._mask_login(account.get("login", credentials["login"])),
                    "account_type": credentials["account_type"],
                    "server": str(account.get("server", credentials["server"])), 
                    "broker": credentials.get("broker", "FxPro"),
                }
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass
            finally:
                _MT5_TERMINAL_LOCK.release()

    def get_dashboard_state(self, user_id: str) -> dict[str, Any]:
        credentials = self._sessions.get(user_id)
        if credentials is None:
            return {
                "connected": False,
                "account": None,
                "positions": [],
                "pending_orders": [],
                "recent_trades": [],
                "symbols": [],
                "open_positions": 0,
                "floating_position_pnl": 0.0,
            }
        broker = self.broker_factory(credentials)
        _MT5_TERMINAL_LOCK.acquire()
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                if str(account.get("account_type", "UNKNOWN")).upper() != credentials["account_type"]:
                    self._sessions.pop(user_id, None)
                    raise MT5DemoError("MT5 account mode changed.")
                positions = list(broker.positions())
                pending = list(broker.pending_orders()) if hasattr(broker, "pending_orders") else []
                history = list(broker.recent_deals(7)) if hasattr(broker, "recent_deals") else []
                symbols: list[dict[str, Any]] = []
                if hasattr(broker, "symbols") and hasattr(broker, "quote"):
                    for item in build_universe(broker.symbols(), top_n=12):
                        try:
                            quote = broker.quote(item.broker_symbol)
                            price = quote.get("last") or quote.get("bid") or quote.get("ask") or 0.0
                            symbols.append({
                                "symbol": item.broker_symbol,
                                "canonical_symbol": item.canonical_symbol,
                                "asset_class": item.asset_class,
                                "opportunity_score": item.opportunity_score,
                                "price": float(price),
                            })
                        except Exception:
                            continue
                return {
                    "connected": True,
                    "account": {
                        "account_masked": self._mask_login(account.get("login", credentials["login"])),
                        "account_type": credentials["account_type"],
                        "server": str(account.get("server", credentials["server"])),
                        "broker": credentials.get("broker", "FxPro"),
                        "balance": float(account.get("balance", 0.0) or 0.0),
                        "equity": float(account.get("equity", 0.0) or 0.0),
                        "currency": str(account.get("currency", "")),
                    },
                    "positions": positions,
                    "pending_orders": pending,
                    "recent_trades": history,
                    "symbols": symbols,
                    "open_positions": len(positions),
                    "floating_position_pnl": round(sum(float(p.get("profit", 0.0) or 0.0) for p in positions), 2),
                }
        except MT5DemoError:
            raise
        except Exception as exc:
            raise MT5DemoError("Unable to read MT5 Demo dashboard state.") from exc
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass
            finally:
                _MT5_TERMINAL_LOCK.release()

    def manual_trading_state(self, user_id: str) -> dict[str, Any]:
        session = self._sessions.get(user_id)
        if not session:
            return {"connected": False, "active": False, "account_type": None}
        mode = session["account_type"]
        if session.get("attach_current"):
            return {"connected": True, "active": False, "account_type": mode,
                    "account_masked": self._mask_login(session["login"]), "server_enabled": False}
        if mode == "DEMO" and self._demo_runtime_managed:
            self.demo_orders_enabled = get_demo_execution_enabled()
        enabled = self.demo_orders_enabled if mode == "DEMO" else self.real_orders_enabled
        active = bool(enabled and (mode == "DEMO" or self._active_real.get(user_id) == session["login"]))
        return {"connected": True, "active": active, "account_type": mode,
                "account_masked": self._mask_login(session["login"]), "server_enabled": enabled}

    def activate_manual_trading(self, user_id: str, account_type: str) -> dict[str, Any]:
        session = self._sessions.get(user_id)
        if not session or session["account_type"] != account_type:
            raise MT5DemoError("Connect the matching MT5 account first.")
        if account_type != "REAL":
            raise MT5DemoError("Demo trading is available after connecting a Demo account.")
        if not self.real_orders_enabled:
            raise MT5DemoError("Real trading is disabled on the server.")
        self._active_real[user_id] = session["login"]
        return self.manual_trading_state(user_id)

    def place_manual_order(self, user_id: str, order: dict[str, Any]) -> dict[str, Any]:
        session = self._sessions.get(user_id)
        if not session:
            raise MT5DemoError("Connect an MT5 account first.")
        mode = session["account_type"]
        if order.get("confirmed") is not True or order.get("account_type") != mode:
            raise MT5DemoError("Confirm the order for the connected account type.")
        if not self.manual_trading_state(user_id)["active"]:
            raise MT5DemoError("Activate trading for this account or ask the owner to enable it.")
        request_id = str(order.get("request_id") or "")
        if len(request_id) < 8 or len(request_id) > 64:
            raise MT5DemoError("A unique order request ID is required.")
        broker = self.execution_factory(session)
        with _MT5_TERMINAL_LOCK:
            if not self.audit.reserve(user_id, request_id, self._mask_login(session["login"]),
                                      mode, order["symbol"], order["direction"], order["volume"]):
                raise MT5DemoError("This order request was already submitted; inspect MT5 history.")
            try:
                account = broker.connect()
                if str(account.get("account_type", "")).upper() != mode or int(account.get("login", -1)) != session["login"]:
                    raise MT5DemoError("MT5 account changed before order submission.")
                if not account.get("trade_allowed", False):
                    raise MT5DemoError("MT5 account does not allow trading.")
                result = broker.market_order(
                    symbol=order["symbol"], direction=order["direction"], volume=order["volume"],
                    stop_loss=order["stop_loss"], take_profit=order["take_profit"],
                    expected_account_type=mode, expected_login=session["login"], comment="ATLAS-MANUAL",
                )
                if result.get("status") != "FILLED":
                    raise MT5DemoError("Broker did not confirm a fill.")
                self.audit.finish(user_id, request_id, "FILLED", result.get("ticket"))
                return result
            except MT5ExecutionError as exc:
                self.audit.finish(user_id, request_id, "UNKNOWN")
                raise MT5DemoError("Broker did not confirm the order. Inspect MT5 history before retrying.") from exc
            except MT5DemoError:
                self.audit.finish(user_id, request_id, "REJECTED")
                raise
            except Exception as exc:
                self.audit.finish(user_id, request_id, "UNKNOWN")
                raise MT5DemoError("Order outcome unknown. Inspect MT5 history before retrying.") from exc
            finally:
                try:
                    broker.disconnect()
                except Exception:
                    pass

    def session_credentials(self, user_id: str) -> dict[str, Any] | None:
        value = self._sessions.get(user_id)
        return deepcopy(value) if value else None
