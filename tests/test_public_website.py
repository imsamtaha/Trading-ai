from fastapi.testclient import TestClient

from app.main import app
from scripts.build_website import validate


def test_public_home_and_assets_work_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "text/html" in page.headers["content-type"]
        assert "ATLAS ULTIMATE" in page.text
        for asset in (
            "site.css", "site.js", "demo-model.js", "favicon.svg", "google-auth.js",
            "atlas-brand.css", "atlas-main-logo.svg",
        ):
            assert client.get(f"/assets/{asset}").status_code == 200
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
