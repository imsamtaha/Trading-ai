"""Contract checks for the private FxPro cTrader read-only transition."""
from pathlib import Path


def test_whish_owner_and_public_support_are_kept_separate():
    root = Path(__file__).resolve().parents[1]
    template = (root / ".env.example").read_text(encoding="utf-8")
    whish = (root / "runtime/private-api/app/billing/whish.py").read_text(encoding="utf-8")
    assert "ATLAS_OWNER_EMAIL=business.samirtaha@gmail.com" in template
    assert "ATLAS_WHISH_SUPPORT=info@justai-atlas.online" in template
    assert 'ADMIN_EMAIL = "imsamtaha.ai@gmail.com"' in whish
