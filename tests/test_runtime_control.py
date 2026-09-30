from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.supabase_auth import AuthenticatedUser
from app.runtime_control import routes


class FakeRuntime:
    def __init__(self):
        self.demo_enabled = False
        self.restarted = False

    def status(self):
        return {"backend": "ONLINE", "demo_execution": self.demo_enabled, "live_execution": "LOCKED", "restart_supported": True}

    def set_demo_execution(self, enabled: bool):
        self.demo_enabled = enabled
        return self.status()

    def restart(self):
        self.restarted = True
        return {"status": "RESTARTING"}


def make_client(monkeypatch, email: str):
    fake = FakeRuntime()
    monkeypatch.setenv("ATLAS_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setattr(routes, "service", fake)
    monkeypatch.setattr(routes, "require_user", lambda request: AuthenticatedUser("u1", email))
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), fake


def test_runtime_status_is_owner_only(monkeypatch):
    client, _ = make_client(monkeypatch, "customer@example.com")
    assert client.get("/api/runtime/status").status_code == 403


def test_owner_can_toggle_demo_execution(monkeypatch):
    client, fake = make_client(monkeypatch, "owner@example.com")
    response = client.post("/api/runtime/demo-execution", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["demo_execution"] is True
    assert fake.demo_enabled is True


def test_owner_can_request_backend_restart(monkeypatch):
    client, fake = make_client(monkeypatch, "owner@example.com")
    response = client.post("/api/runtime/restart")
    assert response.status_code == 202
    assert response.json()["status"] == "RESTARTING"
    assert fake.restarted is True
