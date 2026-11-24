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
            "atlas-brand.css", "atlas-main-logo.svg", "atlas-market.css", "atlas-market.js",
            "atlas-tiger.webp", "atlas-tiger-small.webp", "just-ai-intelligence.webp",
            "just-ai-intelligence-mark.webp",
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


def test_market_link_and_historical_exercise_resolve_in_dashboard_only_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    with TestClient(app) as client:
        page = client.get("/").text
        assert page.index('id="market-analysis"') < page.index('id="marketBoard"')
        assert "/assets/atlas-market.js" in page
        legacy = client.get("/traders", follow_redirects=False)
        assert legacy.status_code == 308
        assert legacy.headers["location"] == "/#market-analysis"
        assert 'href="/#market-analysis"' in client.get("/centers").text
        exercise = client.get("/council/btc-2026-08-31.html")
        assert exercise.status_code == 200
        assert "Awaiting submissions" in exercise.text
        assert exercise.text.count("<summary>STC-") == 9
