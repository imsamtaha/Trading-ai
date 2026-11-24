"""Contract checks for the private FxPro cTrader read-only transition."""
from pathlib import Path

from app.dashboard import _atlas_ultimate_html


def test_ctrader_workspace_has_no_legacy_mt5_onboarding_or_demo_panel(monkeypatch):
    monkeypatch.setenv("ATLAS_BROKER_PROVIDER", "ctrader")
    monkeypatch.setenv("ATLAS_MT5_CONNECTIONS_PAUSED", "true")
    html = _atlas_ultimate_html()
    assert "FxPro cTrader Demo" in html
    assert "FxPro cTrader Demo · read-only" in html
    assert 'id="legacy-mt5-paused" hidden' in html
    assert 'href="/connect/fxpro-mt5"' not in html
    assert '<script src="/ui/demo-panel.js"></script>' not in html
    assert "CTRADER · VIEW ONLY" in html
    assert "Historical MT5 PAPER records are not cTrader broker results." in html


def test_mt5_onboarding_remains_legacy_only_in_mt5_mode(monkeypatch):
    monkeypatch.setenv("ATLAS_BROKER_PROVIDER", "mt5")
    monkeypatch.delenv("ATLAS_MT5_CONNECTIONS_PAUSED", raising=False)
    html = _atlas_ultimate_html()
    assert "FXPRO MT5 ENTRY" in html
    assert '<script src="/ui/demo-panel.js"></script>' in html


def test_whish_owner_and_public_support_are_kept_separate():
    root = Path(__file__).resolve().parents[1]
    template = (root / ".env.example").read_text(encoding="utf-8")
    whish = (root / "runtime/private-api/app/billing/whish.py").read_text(encoding="utf-8")
    assert "ATLAS_OWNER_EMAIL=business.samirtaha@gmail.com" in template
    assert "ATLAS_WHISH_SUPPORT=info@justai-atlas.online" in template
    assert 'ADMIN_EMAIL = "imsamtaha.ai@gmail.com"' in whish
