from fastapi.testclient import TestClient
from app.main import app


def test_assistant_requires_authenticated_session(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    assert TestClient(app).post("/api/user/assistant", json={"message": "Explain drawdown"}).status_code == 401


def test_assistant_accepts_only_bounded_message_and_user_identity(monkeypatch):
    import app.users.routes as routes
    from app.auth.supabase_auth import AuthenticatedUser

    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("user-a"))
    monkeypatch.setattr(routes, "answer_assistant", lambda user_id, message: f"{user_id}: {message}")
    client = TestClient(app)
    assert client.post("/api/user/assistant", json={"message": "Explain risk"}).json() == {"message": "user-a: Explain risk"}
    assert client.post("/api/user/assistant", json={"message": "x" * 1001}).status_code == 422
    assert client.post("/api/user/assistant", json={"message": ""}).status_code == 422

def test_assistant_sends_only_prompt_to_provider(monkeypatch):
    import app.users.assistant as assistant

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []
    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("Result", (), {"output_text": "Educational answer"})()
    monkeypatch.setattr(assistant, "_client", lambda: type("Client", (), {"responses": FakeResponses()})())
    assert assistant.answer_assistant("private-user-id", "Explain risk") == "Educational answer"
    assert calls[0]["input"] == "Explain risk"
    assert "private-user-id" not in str(calls[0])
    assert calls[0]["store"] is False
    assert calls[0]["max_output_tokens"] <= 300
