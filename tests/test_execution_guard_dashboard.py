from fastapi.testclient import TestClient


def test_dashboard_exposes_execution_guard_feature_and_status(monkeypatch):
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
    monkeypatch.setattr(user_routes, "repository", repo)
    monkeypatch.setattr(user_routes, "require_user", lambda request: AuthenticatedUser("user-a", "a@example.com"))
    monkeypatch.setattr(mt5_routes, "service", FakeMT5())
    monkeypatch.setattr(guard_routes, "service", FakeGuard())

    payload = TestClient(app).get("/api/user/dashboard").json()
    assert payload["features"]["execution_guard"] is False
    assert payload["execution_guard"]["status"] == "READY"


def test_paid_plan_exposes_execution_guard_feature(monkeypatch):
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
    repo.get_or_create_profile("user-a")
    repo.subscriptions["user-a"] = {"user_id": "user-a", "plan": "STARTER", "status": "ACTIVE", "billing_reference": "ATLAS-TEST", "expires_at": "2099-01-01T00:00:00+00:00"}
    monkeypatch.setattr(user_routes, "repository", repo)
    monkeypatch.setattr(user_routes, "require_user", lambda request: AuthenticatedUser("user-a", "a@example.com"))
    monkeypatch.setattr(mt5_routes, "service", FakeMT5())
    monkeypatch.setattr(guard_routes, "service", FakeGuard())
    payload = TestClient(app).get("/api/user/dashboard").json()
    assert payload["features"]["execution_guard"] is True
