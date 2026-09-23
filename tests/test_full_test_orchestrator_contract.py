from pathlib import Path

SCRIPT = Path("scripts/run_full_atlas_test.ps1")


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_orchestrator_hard_codes_safe_validation_flags():
    text = _text()
    assert "$env:ATLAS_LIVE_TRADING = 'false'" in text
    assert "$env:MT5_REQUIRE_DEMO = 'true'" in text


def test_required_groups_are_present():
    text = _text()
    for name in [
        "repo_tests",
        "web_tests",
        "risk_safety",
        "api_smoke",
        "windows_integrity",
        "mt5_demo_runtime",
        "restart_reconnect",
    ]:
        assert name in text


def test_repository_and_web_commands_are_orchestrated():
    text = _text()
    assert "python -m pytest -q" in text
    assert "node --check web/assets/site.js" in text
    assert "node --test tests/test_demo_model.cjs" in text
    assert "node --test tests/test_google_auth.mjs" in text
    assert "python scripts/build_website.py" in text


def test_risk_and_windows_integrity_commands_are_orchestrated():
    text = _text()
    assert "tests/test_signal_journal_integrity.py" in text
    assert "tests/test_atlas_demo_status_integrity.py" in text
    assert "scripts/deploy_google_cloud.ps1" in text


def test_api_smoke_requires_health_and_blocked_execution_path():
    text = _text()
    assert "/health" in text
    assert "/mt5/test-order" in text
    assert "403" in text


def test_mt5_runtime_uses_existing_demo_entry_points():
    text = _text()
    assert "python scripts/verify_mt5.py" in text
    assert "python run_atlas_mt5.py --once" in text
    assert "DEMO" in text


def test_restart_reconnect_never_claims_unproven_pass():
    text = _text()
    assert "restart_reconnect" in text
    assert "PARTIAL" in text
