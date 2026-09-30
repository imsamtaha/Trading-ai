from fastapi.testclient import TestClient


def test_configured_owner_email_gets_private_owner_dashboard(monkeypatch):
    from app.main import app
    import app.users.routes as user_routes
    import app.mt5_demo.routes as mt5_routes
    import app.execution_guard.routes as guard_routes
    from app.auth.supabase_auth import AuthenticatedUser
    from app.users.repository import MemoryUserRepository

    class FakeMT5:
        def get_dashboard_state(self, user_id):
            return {"connected": False, "account": None, "positions": [], "pending_orders": [], "recent_trades": [], "symbols": []}

    class FakeGuard:
        def status(self, user_id):
            return {"status": "READY", "last_event": None}

    repo = MemoryUserRepository()
    monkeypatch.setenv("ATLAS_OWNER_EMAIL", "atlas-intelligence@gmail.com")
    monkeypatch.setattr(user_routes, "repository", repo)
    monkeypatch.setattr(user_routes, "require_user", lambda request: AuthenticatedUser("owner-1", "Atlas-Intelligence@gmail.com"))
    monkeypatch.setattr(mt5_routes, "service", FakeMT5())
    monkeypatch.setattr(guard_routes, "service", FakeGuard())
    payload = TestClient(app).get("/api/user/dashboard").json()
    assert payload["user"]["role"] == "OWNER"
    assert payload["plan"] == "OWNER"
    assert payload["features"]["execution_guard"] is True
