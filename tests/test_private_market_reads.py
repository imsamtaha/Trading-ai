from fastapi.testclient import TestClient
from app.main import app


def test_private_chart_and_briefing_require_session(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    client = TestClient(app)
    assert client.get("/api/user/chart-data").status_code == 401
    assert client.get("/api/user/market-briefing").status_code == 401


def test_private_chart_validates_inputs_after_auth(monkeypatch):
    from app.auth.supabase_auth import AuthenticatedUser
    import app.users.routes as routes
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    monkeypatch.setattr(routes, "get_candles", lambda symbol, interval, limit: {"symbol": symbol, "interval": interval, "count": 1, "candles": [{"time": 1, "open": 1, "high": 2, "low": 1, "close": 2}]})
    client = TestClient(app)
    assert client.get("/api/user/chart-data?symbol=XAUUSD&interval=1h&limit=120").json()["candles"][0]["close"] == 2
    assert client.get("/api/user/chart-data?symbol=BAD&interval=1h").status_code == 400
    assert client.get("/api/user/chart-data?symbol=XAUUSD&interval=3s").status_code == 400


def test_private_briefing_returns_read_only_snapshot(monkeypatch):
    from app.auth.supabase_auth import AuthenticatedUser
    import app.users.routes as routes
    from datetime import datetime, timedelta, timezone
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    repo.get_or_create_profile("user-a")
    repo.subscriptions["user-a"] = {"plan": "STARTER", "status": "ACTIVE", "billing_reference": "ATLAS-PAID",
                                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()}
    monkeypatch.setattr(routes, "repository", repo)
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    monkeypatch.setattr(routes, "get_market_briefing", lambda: {"headlines": [], "market_board": []})
    assert TestClient(app).get("/api/user/market-briefing").json()["headlines"] == []
