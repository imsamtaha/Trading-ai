import pytest
from app.mt5_demo.service import MT5DemoError, MT5DemoService
from app.users.repository import MemoryUserRepository

@pytest.fixture(autouse=True)
def isolated_audit_db(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_TRADE_AUDIT_DB", str(tmp_path / "manual_orders.sqlite3"))

class FakeBroker:
    def __init__(self, credentials, mode="DEMO"):
        self.credentials = credentials
        self.mode = mode
        self.orders = []
    def connect(self):
        return {"login": self.credentials["login"], "account_type": self.mode, "server": self.credentials["server"], "trade_allowed": True}
    def disconnect(self):
        pass
    def market_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"status": "FILLED", "ticket": 42, "symbol": kwargs["symbol"]}

def test_manual_order_requires_connected_matching_account_and_confirmation():
    brokers = []
    def factory(creds):
        b = FakeBroker(creds, mode="DEMO")
        brokers.append(b)
        return b
    service = MT5DemoService(MemoryUserRepository(), broker_factory=factory, execution_factory=factory, demo_orders_enabled=True)
    service.connect_demo("alice", {"login": 1234, "password": "secret", "server": "FxPro-MT5 Demo"})
    order = {"request_id": "manual-request-1", "account_type": "DEMO", "symbol": "EURUSD", "direction": "BUY", "volume": 0.01, "stop_loss": 1.19, "take_profit": 1.21}
    for user, data in [("bob", {**order, "confirmed": True}), ("alice", order), ("alice", {**order, "account_type": "REAL", "confirmed": True})]:
        with pytest.raises(MT5DemoError):
            service.place_manual_order(user, data)
    assert service.place_manual_order("alice", {**order, "confirmed": True})["ticket"] == 42
    assert brokers[-1].orders[0]["expected_login"] == 1234
    assert brokers[-1].orders[0]["expected_account_type"] == "DEMO"

def test_real_order_requires_explicit_activation_and_server_permission():
    brokers = []
    def factory(creds):
        b = FakeBroker(creds, mode="REAL")
        brokers.append(b)
        return b
    service = MT5DemoService(MemoryUserRepository(), broker_factory=factory, execution_factory=factory, real_orders_enabled=True)
    service.connect_account("alice", {"login": 7777, "password": "secret", "server": "FxPro-MT5 Live"}, "REAL")
    order = {"request_id": "manual-request-2", "account_type": "REAL", "symbol": "EURUSD", "direction": "SELL", "volume": 0.01, "stop_loss": 1.22, "take_profit": 1.18, "confirmed": True}
    with pytest.raises(MT5DemoError, match="Activate"):
        service.place_manual_order("alice", order)
    assert service.activate_manual_trading("alice", "REAL")["active"] is True
    assert service.place_manual_order("alice", order)["status"] == "FILLED"
    service.disconnect_demo("alice")
    with pytest.raises(MT5DemoError):
        service.place_manual_order("alice", order)
    assert len([b for b in brokers if b.orders]) == 1

def test_real_execution_remains_disabled_without_server_switch():
    def factory(creds):
        return FakeBroker(creds, mode="REAL")
    service = MT5DemoService(MemoryUserRepository(), broker_factory=factory, execution_factory=factory, real_orders_enabled=False)
    service.connect_account("alice", {"login": 7777, "password": "secret", "server": "FxPro-MT5 Live"}, "REAL")
    with pytest.raises(MT5DemoError, match="disabled"):
        service.activate_manual_trading("alice", "REAL")

def test_manual_order_route_requires_auth_and_confirmation(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.mt5_demo import routes
    from app.auth.supabase_auth import AuthenticatedUser
    factory = lambda creds: FakeBroker(creds, mode="DEMO")
    service = MT5DemoService(MemoryUserRepository(), broker_factory=factory, execution_factory=factory, demo_orders_enabled=True)
    monkeypatch.setattr(routes, "service", service)
    client = TestClient(app)
    order = {"request_id": "manual-request-1", "account_type": "DEMO", "symbol": "EURUSD", "direction": "BUY", "volume": 0.01, "stop_loss": 1.19, "take_profit": 1.21, "confirmed": True}
    assert client.post("/api/mt5-demo/order", json=order).status_code == 401
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("alice", "a@example.com"))
    service.connect_demo("alice", {"login": 1234, "password": "secret", "server": "FxPro-MT5 Demo"})
    assert client.post("/api/mt5-demo/order", json={**order, "confirmed": False}).status_code == 422
    assert client.post("/api/mt5-demo/order", json=order).json()["ticket"] == 42

def test_duplicate_order_request_id_never_sends_twice():
    brokers = []
    def factory(creds):
        b = FakeBroker(creds)
        brokers.append(b)
        return b
    service = MT5DemoService(MemoryUserRepository(), broker_factory=factory, execution_factory=factory, demo_orders_enabled=True)
    service.connect_demo("alice", {"login": 1234, "password": "secret", "server": "FxPro-MT5 Demo"})
    order = {"request_id": "fixed-request-1", "account_type": "DEMO", "symbol": "EURUSD", "direction": "BUY", "volume": 0.01, "stop_loss": 1.19, "take_profit": 1.21, "confirmed": True}
    service.place_manual_order("alice", order)
    with pytest.raises(MT5DemoError, match="already"):
        service.place_manual_order("alice", order)
    assert sum(len(b.orders) for b in brokers) == 1

def test_manual_order_rejects_cross_origin_cookie_request(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.mt5_demo import routes
    from app.auth.supabase_auth import AuthenticatedUser
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("alice", "a@example.com"))
    client = TestClient(app)
    client.cookies.set("atlas_session", "test-session")
    order = {"request_id": "manual-request-csrf", "account_type": "DEMO", "symbol": "EURUSD",
             "direction": "BUY", "volume": 0.01, "stop_loss": 1.19, "take_profit": 1.21, "confirmed": True}
    response = client.post("/api/mt5-demo/order", json=order, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403

def test_real_execution_switch_alone_does_not_bypass_acknowledgement(monkeypatch):
    monkeypatch.setenv("ATLAS_USER_REAL_ORDERS", "true")
    monkeypatch.delenv("ATLAS_REAL_MONEY_ACK", raising=False)
    service = MT5DemoService(MemoryUserRepository(), broker_factory=lambda creds: FakeBroker(creds, mode="REAL"))
    assert service.real_orders_enabled is False
