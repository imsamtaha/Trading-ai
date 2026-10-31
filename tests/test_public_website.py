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
        assert '/assets/atlas-tiger-shield.png' in page.text
        for asset in (
            "site.css", "site.js", "demo-model.js", "favicon.svg", "google-auth.js",
            "atlas-brand.css", "atlas-main-logo.svg", "atlas-tiger-shield.png",
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


def test_legacy_static_pages_use_same_tiger_shield_logo():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "web"
    logo = root / "assets" / "atlas-tiger-shield.png"
    assert logo.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    for path in (root / "index.html", root / "centers" / "index.html"):
        assert "/assets/atlas-tiger-shield.png" in path.read_text(encoding="utf-8")


def test_tiger_shield_palette_is_present_on_both_website_and_dashboard_headers():
    from pathlib import Path
    from app.dashboard.trading_hub import HUB_HEADER, HUB_STYLE

    root = Path(__file__).resolve().parents[1]
    css = (root / "web" / "assets" / "atlas-brand.css").read_text(encoding="utf-8")
    assert "Tiger Shield header palette" in css
    assert "#102136" in css
    assert "/assets/atlas-tiger-shield.png" in HUB_HEADER
    assert "Tiger Shield / ATLAS palette integration" in HUB_STYLE
    assert "#0b2033" in HUB_STYLE
