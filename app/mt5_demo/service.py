from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Callable

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError


class MT5DemoError(RuntimeError):
    pass


class MT5DemoService:
    def __init__(self, repository: Any, broker_factory: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self.repository = repository
        self.broker_factory = broker_factory or self._default_broker_factory
        self._sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _default_broker_factory(credentials: dict[str, Any]) -> MT5Broker:
        config = MT5Config(
            terminal_path=os.getenv("MT5_TERMINAL_PATH"),
            login=int(credentials["login"]),
            password=str(credentials["password"]),
            server=str(credentials["server"]),
            dry_run=True,
            real_money_execution=False,
        )
        return MT5Broker(config)

    @staticmethod
    def _mask_login(login: int | str) -> str:
        token = str(login)
        return f"***{token[-4:]}" if token else "***"

    def connect_demo(self, user_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
        broker = self.broker_factory(credentials)
        try:
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

    def session_credentials(self, user_id: str) -> dict[str, Any] | None:
        value = self._sessions.get(user_id)
        return deepcopy(value) if value else None
