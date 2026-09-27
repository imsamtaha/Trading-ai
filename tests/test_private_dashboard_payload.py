from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def configure(monkeypatch):
    secret = "test-secret-key-that-is-long-enough-123456"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    return secret


def token(secret: str, user_id: str) -> str:
    return jwt.encode({
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }, secret, algorithm="HS256")


class FakeDemoService:
    def get_dashboard_state(self, user_id):
        suffix = "1111" if user_id == "user-a" else "2222"
        return {
            "connected": True,
            "account": {"account_masked": f"***{suffix}", "account_type": "DEMO", "balance": 1000.0, "equity": 995.0},
            "positions": [{"symbol": "EURUSD", "direction": "LONG", "profit": -5.0, "owner": user_id}],
            "pending_orders": [],
            "recent_trades": [{"symbol": "GOLD", "profit": 12.0, "owner": user_id}],
            "symbols": [],
        }


def test_private_dashboard_payload_is_user_scoped(monkeypatch):
    secret = configure(monkeypatch)
    from app.main import app
    import app.users.routes as user_routes
    import app.mt5_demo.routes as mt5_routes
    from app.users.repository import MemoryUserRepository

    repo = MemoryUserRepository()
    monkeypatch.setattr(user_routes, "repository", repo)
    monkeypatch.setattr(mt5_routes, "service", FakeDemoService())
    client = TestClient(app)
    client.cookies.set("atlas_session", token(secret, "user-a"))
    response = client.get("/api/user/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"] == "FREE"
    assert payload["mt5"]["account"]["account_masked"] == "***1111"
    assert payload["mt5"]["positions"][0]["owner"] == "user-a"
    assert "user-b" not in response.text


def test_private_dashboard_html_uses_private_api_and_activity_tabs():
    from app.dashboard.views import DASHBOARD_HTML
    assert "/api/user/dashboard" in DASHBOARD_HTML
    assert 'id="accountBadge"' in DASHBOARD_HTML
    for token in ('data-activity-tab="open"', 'data-activity-tab="pending"', 'data-activity-tab="history"'):
        assert token in DASHBOARD_HTML
    assert "FREE" in DASHBOARD_HTML


def test_private_dashboard_labels_have_arabic_translations():
    from app.dashboard.preferences import SCRIPT
    for pair in (
        "'MT5 Activity':'نشاط MT5'",
        "'Pending':'معلّقة'",
        "'History':'السجل'",
        "'Logout':'تسجيل الخروج'",
        "'READ ONLY':'للقراءة فقط'",
    ):
        assert pair in SCRIPT
