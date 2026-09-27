from __future__ import annotations

import os
import threading
from copy import deepcopy
from typing import Any, Callable

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.strategy.universe import build_universe

_MT5_TERMINAL_LOCK = threading.RLock()


class MT5DemoError(RuntimeError):
    pass


class MT5DemoService:
    def __init__(self, repository: Any, broker_factory: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self.repository = repository
        self.broker_factory = broker_factory or self._default_broker_factory
        self._sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _default_broker_factory(credentials: dict[str, Any]) -> MT5Broker:
        return MT5Broker(MT5Config(
            terminal_path=os.getenv("MT5_TERMINAL_PATH"),
            login=int(credentials["login"]),
            password=str(credentials["password"]),
            server=str(credentials["server"]),
            dry_run=True,
            real_money_execution=False,
        ))

    @staticmethod
    def _mask_login(login: int | str) -> str:
        token = str(login)
        return f"***{token[-4:]}" if token else "***"

    def connect_demo(self, user_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
        broker = self.broker_factory(credentials)
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                account_type = str(account.get("account_type", "UNKNOWN")).upper()
                if account_type != "DEMO":
                    raise MT5DemoError("Only verified MT5 DEMO accounts are supported.")
            metadata = {
                "account_masked": self._mask_login(account.get("login", credentials.get("login"))),
                "account_type": "DEMO",
                "server": str(account.get("server", credentials.get("server", ""))),
                "broker": str(credentials.get("broker", "FxPro")),
                "connection_state": "CONNECTED",
            }
            self._sessions[user_id] = {
                "login": int(credentials["login"]),
                "password": str(credentials["password"]),
                "server": str(credentials["server"]),
                "broker": str(credentials.get("broker", "FxPro")),
            }
            self.repository.set_mt5_connection(user_id, metadata)
            return {**metadata, "connected": True}
        except MT5DemoError:
            raise
        except (MT5ExecutionError, KeyError, TypeError, ValueError) as exc:
            raise MT5DemoError("Unable to verify MT5 Demo account.") from exc
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass

    def disconnect_demo(self, user_id: str) -> dict[str, Any]:
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
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                account_type = str(account.get("account_type", "UNKNOWN")).upper()
                if account_type != "DEMO":
                    self._sessions.pop(user_id, None)
                    raise MT5DemoError("MT5 account is no longer verified as DEMO.")
                return {
                    "connected": True,
                    "account_masked": self._mask_login(account.get("login", credentials["login"])),
                    "account_type": "DEMO",
                    "server": str(account.get("server", credentials["server"])),
                    "broker": credentials.get("broker", "FxPro"),
                }
        finally:
            try:
                broker.disconnect()
            except Exception:
                pass

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
        try:
            with _MT5_TERMINAL_LOCK:
                account = broker.connect()
                if str(account.get("account_type", "UNKNOWN")).upper() != "DEMO":
                    self._sessions.pop(user_id, None)
                    raise MT5DemoError("MT5 account is no longer verified as DEMO.")
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
                        "account_type": "DEMO",
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

    def session_credentials(self, user_id: str) -> dict[str, Any] | None:
        value = self._sessions.get(user_id)
        return deepcopy(value) if value else None
