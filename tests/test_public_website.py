from fastapi.testclient import TestClient

from app.main import app
from scripts.build_website import validate


def test_service_entry_and_public_auth_asset_work_in_read_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    with TestClient(app) as client:
        assert client.get("/").json()["api"] == "/api"
        assert client.get("/assets/google-auth.js").status_code == 200
        assert client.get("/assets/site.js").status_code == 404
        assert client.get("/api").json()["system"] == "ATLAS ULTIMATE"


def test_public_assets_cannot_read_private_files_and_orders_stay_blocked(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    with TestClient(app) as client:
        for path in ("/assets/.env", "/assets/main.py", "/assets/requirements.txt"):
            assert client.get(path).status_code == 404
        assert client.post("/mt5/test-order").status_code == 403
        assert client.get("/mt5/positions").status_code == 403


def test_public_package_is_complete_and_has_no_private_configuration():
    validate()


def test_historical_council_exercise_remains_available(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    with TestClient(app) as client:
        exercise = client.get("/council/btc-2026-08-31.html")
        assert exercise.status_code == 200
        assert "Awaiting submissions" in exercise.text
        assert exercise.text.count("<summary>STC-") == 9
