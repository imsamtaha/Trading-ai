from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class FakeBroker:
    account_type: str
    login: int
    server: str
    connected: bool = False

    def connect(self):
        self.connected = True
        return {
            "login": self.login,
            "server": self.server,
            "account_type": self.account_type,
            "balance": 10000.0,
            "equity": 9990.0,
            "currency": "USD",
            "trade_allowed": True,
            "real_money_execution_enabled": False,
        }

    def disconnect(self):
        self.connected = False

    def positions(self):
        return []


def make_factory(types):
    def factory(credentials):
        return FakeBroker(types[credentials["login"]], credentials["login"], credentials["server"])
    return factory


def test_connect_accepts_demo_and_masks_account():
    from app.mt5_demo.service import MT5DemoService
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    service = MT5DemoService(repo, broker_factory=make_factory({11112222: "DEMO"}))
    state = service.connect_demo("user-a", {"login": 11112222, "password": "secret", "server": "FxPro-MT5 Demo"})
    assert state["account_masked"] == "***2222"
    assert state["account_type"] == "DEMO"
    assert "password" not in state
    assert "password" not in repo.get_mt5_connection("user-a")


@pytest.mark.parametrize("account_type", ["REAL", "CONTEST", "UNKNOWN"])
def test_connect_rejects_non_demo(account_type):
    from app.mt5_demo.service import MT5DemoError, MT5DemoService
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    service = MT5DemoService(repo, broker_factory=make_factory({12345678: account_type}))
    with pytest.raises(MT5DemoError):
        service.connect_demo("user-a", {"login": 12345678, "password": "secret", "server": "FxPro"})
    assert repo.get_mt5_connection("user-a") is None


def test_sessions_are_isolated_between_users():
    from app.mt5_demo.service import MT5DemoService
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    factory = make_factory({11112222: "DEMO", 33334444: "DEMO"})
    service = MT5DemoService(repo, broker_factory=factory)
    service.connect_demo("user-a", {"login": 11112222, "password": "a", "server": "FxPro-MT5 Demo"})
    service.connect_demo("user-b", {"login": 33334444, "password": "b", "server": "FxPro-MT5 Demo"})
    assert service.get_demo_state("user-a")["account_masked"] == "***2222"
    assert service.get_demo_state("user-b")["account_masked"] == "***4444"
    service.disconnect_demo("user-a")
    assert service.get_demo_state("user-a")["connected"] is False
    assert service.get_demo_state("user-b")["connected"] is True



def test_real_connection_is_read_only_and_requires_explicit_real_mode():
    from app.mt5_demo.service import MT5DemoError, MT5DemoService
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    service = MT5DemoService(repo, broker_factory=make_factory({12345678: "REAL", 11112222: "DEMO"}))
    with pytest.raises(MT5DemoError):
        service.connect_account("user-a", {"login": 11112222, "password": "x", "server": "FxPro"}, "REAL")
    result = service.connect_account("user-a", {"login": 12345678, "password": "x", "server": "FxPro"}, "REAL")
    assert result["account_type"] == "REAL"
    assert result["real_money_execution_enabled"] is False
    assert "password" not in repo.get_mt5_connection("user-a")
    assert service.get_dashboard_state("user-a")["account"]["account_type"] == "REAL"



def test_real_route_requires_login_and_keeps_execution_disabled(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.mt5_demo import routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository
    service = routes.MT5DemoService(MemoryUserRepository(), broker_factory=make_factory({12345678: "REAL"}))
    monkeypatch.setattr(routes, "service", service)
    client = TestClient(app)
    assert client.post("/api/mt5-demo/connect-real", json={"login": 12345678, "password": "x", "server": "FxPro"}).status_code == 401
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a", "a@example.com"))
    response = client.post("/api/mt5-demo/connect-real", json={"login": 12345678, "password": "x", "server": "FxPro"})
    assert response.status_code == 200
    assert response.json()["real_money_execution_enabled"] is False
