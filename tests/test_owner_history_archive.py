import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("owner,login", [(True, 592031391), (True, 123456), (False, 592031391)])
def test_history_archive_keeps_positions_and_future_deals(monkeypatch, owner, login):
    from app.main import app
    import app.users.routes as routes
    import app.mt5_demo.routes as mt5_routes
    import app.execution_guard.routes as guard_routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    history = [
        {"ticket": 323402061, "time": 1790880044, "profit": 5},
        {"ticket": 323402062, "time": 1790880045, "profit": 6},
    ]
    positions = [{"ticket": 123, "symbol": "EURUSD", "profit": -2}]
    pending = [{"ticket": 456, "symbol": "GBPUSD"}]

    class FakeMT5:
        def session_credentials(self, user_id):
            return {"login": login, "server": "FxPro-MT5 Demo"}
        def get_dashboard_state(self, user_id):
            return {"connected": True, "positions": positions, "pending_orders": pending,
                    "recent_trades": list(history), "open_positions": 1,
                    "account": {"balance": 1000, "equity": 998},
                    "floating_position_pnl": -2}

    class FakeGuard:
        def status(self, user_id):
            return {"status": "READY"}

    monkeypatch.setenv("ATLAS_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setattr(routes, "repository", MemoryUserRepository())
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser(
        "owner-1" if owner else "customer-1", "owner@example.com" if owner else "customer@example.com"))
    monkeypatch.setattr(mt5_routes, "service", FakeMT5())
    monkeypatch.setattr(guard_routes, "service", FakeGuard())
    response = TestClient(app).get("/api/user/dashboard")
    assert response.status_code == 200
    result = response.json()["mt5"]
    assert result["positions"] == positions
    assert result["pending_orders"] == pending
    assert result["open_positions"] == 1
    assert result["account"] == {"balance": 1000, "equity": 998}
    assert result["floating_position_pnl"] == -2
    expected = [history[1]] if owner and login == 592031391 else history
    assert result["recent_trades"] == expected
