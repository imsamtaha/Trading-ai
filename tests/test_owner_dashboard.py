"""Owner /sam protection, verified-only data and strict execution isolation."""
import base64
import json

from fastapi.testclient import TestClient

from app.main import app


def _auth(user="sam", password="long-test-owner-password-2026"):
    value = base64.b64encode((user + ":" + password).encode()).decode()
    return {"Authorization": "Basic " + value}


def test_owner_is_fail_closed_without_credentials(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.delenv("ATLAS_OWNER_DASHBOARD_PASSWORD", raising=False)
    with TestClient(app) as client:
        for url in ("/sam", "/sam/", "/sam/assets/owner.js", "/sam/api/snapshot"):
            response = client.get(url)
            assert response.status_code == 503
        assert client.post("/mt5/test-order").status_code == 403


def test_owner_auth_and_assets_are_private(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "long-test-owner-password-2026")
    monkeypatch.delenv("ATLAS_OWNER_EVIDENCE_DIR", raising=False)
    with TestClient(app) as client:
        assert client.get("/sam").status_code == 401
        assert client.get("/sam/api/snapshot").status_code == 401
        assert client.get("/sam", headers=_auth(password="wrong")).status_code == 401
        page = client.get("/sam", headers=_auth())
        assert page.status_code == 200
        assert 'lang="ar" dir="rtl"' in page.text
        assert "LIVE TRADING DISABLED" in page.text
        assert "no-store" in page.headers["cache-control"]
        assert "noindex" in page.headers["x-robots-tag"]
        assert client.get("/sam/assets/owner.js", headers=_auth()).status_code == 200
        assert client.get("/sam/assets/owner.css", headers=_auth()).status_code == 200
        assert client.get("/sam/assets/.env", headers=_auth()).status_code in (403, 404)
        assert client.post("/sam/api/snapshot", headers=_auth()).status_code == 403


def test_snapshot_never_fakes_metrics_without_evidence(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "long-test-owner-password-2026")
    monkeypatch.delenv("ATLAS_OWNER_EVIDENCE_DIR", raising=False)
    with TestClient(app) as client:
        data = client.get("/sam/api/snapshot", headers=_auth()).json()
        assert data["mode"] == "PAPER_READ_ONLY"
        assert data["live_orders_allowed"] is False
        assert data["broker_execution_allowed"] is False
        assert data["datasets"]["paper_trades"] == []
        assert data["datasets"]["overview"] == {}
        assert data["evidence"]["overview"]["status"] == "UNAVAILABLE"


def test_unverified_exports_not_displayed_and_verified_export_is_filtered(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_OWNER_DASHBOARD_PASSWORD", "long-test-owner-password-2026")
    monkeypatch.setenv("ATLAS_OWNER_EVIDENCE_DIR", str(tmp_path))
    (tmp_path / "overview.json").write_text(json.dumps({
        "verification": "PENDING", "data": {"paper_closed": 999999},
    }), encoding="utf-8")
    (tmp_path / "agents.json").write_text(json.dumps({
        "verification": "VERIFIED",
        "provenance": {"source": "Windows council export",
                       "verified_at": "2026-11-07T03:00:00Z",
                       "method": "Owner reviewed against journal"},
        "data": [{"name": "Risk agent", "confidence": 0.81,
                  "secret": "sensitive broker token", "vote": "VETO"}],
    }), encoding="utf-8")
    with TestClient(app) as client:
        data = client.get("/sam/api/snapshot", headers=_auth()).json()
    assert data["datasets"]["overview"] == {}
    assert data["evidence"]["overview"]["status"] == "UNVERIFIED"
    assert data["evidence"]["agents"]["status"] == "VERIFIED_EXPORT"
    assert data["datasets"]["agents"] == [
        {"name": "Risk agent", "confidence": 0.81, "vote": "VETO"}]
    assert "sensitive broker token" not in json.dumps(data)


def test_trader_uses_separate_readonly_route(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.delenv("ATLAS_OWNER_DASHBOARD_PASSWORD", raising=False)
    with TestClient(app) as client:
        res = client.get("/traders")
        assert res.status_code == 200
        assert "TRADER WORKSPACE" in res.text
        assert "LIVE TRADING DISABLED" in res.text
        assert "/sam/api/snapshot" not in res.text
        assert client.post("/traders").status_code == 403
