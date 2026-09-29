from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app.main import app


def payload():
    return {
        "decision_id": "route-decision-1", "symbol": "EURUSD", "direction": "BUY",
        "confidence": 85, "rationale": "Council consensus", "timestamp": datetime.now(UTC).isoformat(),
        "volume": 0.01, "stop_loss": 1.09, "take_profit": 1.11, "risk_context": {},
    }


def test_execution_guard_routes_require_authentication():
    client = TestClient(app)
    assert client.get("/api/execution-guard/status").status_code == 401
    assert client.post("/api/execution-guard/evaluate", json=payload()).status_code == 401


def test_execution_guard_cookie_posts_enforce_same_origin(monkeypatch):
    from app.execution_guard import routes
    from app.auth.supabase_auth import AuthenticatedUser
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("alice", "a@example.com"))
    client = TestClient(app)
    client.cookies.set("atlas_session", "test-session")
    assert client.post("/api/execution-guard/evaluate", json=payload(), headers={"Origin": "https://evil.example"}).status_code == 403


def test_execution_guard_routes_return_user_scoped_status_and_events(monkeypatch):
    from app.execution_guard import routes
    from app.auth.supabase_auth import AuthenticatedUser

    class FakeService:
        def evaluate(self, user_id, decision):
            from app.execution_guard.models import GuardResult
            return GuardResult(decision_id=decision.decision_id, status="BLOCKED", reason="test")
        def status(self, user_id): return {"status": "READY", "user_id": user_id}
        def events(self, user_id): return [{"status": "BLOCKED", "user_id": user_id}]
        def confirm(self, user_id, draft_id): raise ValueError("Live broker execution is disabled for this deployment.")

    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("alice", "a@example.com"))
    monkeypatch.setattr(routes, "service", FakeService())
    client = TestClient(app)
    headers = {"Origin": "https://justai-atlas.online"}
    assert client.post("/api/execution-guard/evaluate", json=payload(), headers=headers).json()["status"] == "BLOCKED"
    assert client.get("/api/execution-guard/status").json()["user_id"] == "alice"
    assert client.get("/api/execution-guard/events").json()[0]["user_id"] == "alice"
    assert client.post("/api/execution-guard/confirm/draft-1", headers=headers).status_code == 409
