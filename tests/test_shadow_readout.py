import json
from datetime import datetime, timedelta, timezone

from app.dashboard.shadow_readout import read_shadow_summary
from app.dashboard.demo_panel import SCRIPT


NOW = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)


def profile(**overrides):
    value = {
        "version": 1,
        "generated_at": (NOW - timedelta(hours=1)).isoformat(),
        "training_environment": "PAPER",
        "broker_execution_allowed": False,
        "minimum_samples": 5,
        "total_examples": 10,
        "agents": {
            "A": {"samples": 6, "weight": 1.2, "locked_baseline": False},
            "B": {"samples": 3, "weight": 1.0, "locked_baseline": True},
        },
    }
    value.update(overrides)
    return value


def write(tmp_path, value):
    target = tmp_path / "profile.json"
    target.write_text(json.dumps(value), encoding="utf-8")
    return target


def test_missing_profile_is_not_training_success(tmp_path):
    result = read_shadow_summary(path=tmp_path / "missing.json", now=NOW)
    assert result["status"] == "MISSING"
    assert result["settled_paper_examples"] is None
    assert result["automatic_live_activation"] is False


def test_valid_profile_is_aggregated_without_private_opinions(tmp_path):
    result = read_shadow_summary(path=write(tmp_path, profile()), now=NOW)
    assert result["status"] == "FRESH"
    assert result["settled_paper_examples"] == 10
    assert result["agents_observed"] == 2
    assert result["agents_calibrated"] == 1
    assert result["agents_at_baseline"] == 1
    assert result["broker_execution_allowed"] is False
    assert "agents" not in result
    assert "snapshot_id" not in str(result)


def test_old_profile_is_marked_stale(tmp_path):
    target = write(tmp_path, profile(generated_at=(NOW - timedelta(days=2)).isoformat()))
    assert read_shadow_summary(path=target, now=NOW)["status"] == "STALE"


def test_nonpaper_and_broker_executed_profiles_are_invalid(tmp_path):
    for overrides in ({"training_environment": "LIVE"}, {"broker_execution_allowed": True}):
        assert read_shadow_summary(path=write(tmp_path, profile(**overrides)), now=NOW)["status"] == "INVALID"


def test_invalid_and_nonfinite_agent_weights_fail_closed(tmp_path):
    for weight in (1.7, -0.4, float("nan"), "Infinity"):
        row = profile()
        row["agents"]["A"]["weight"] = weight
        assert read_shadow_summary(path=write(tmp_path, row), now=NOW)["status"] == "INVALID"


def test_invalid_sample_locks_or_future_dates_fail_closed(tmp_path):
    row = profile()
    row["agents"]["B"]["locked_baseline"] = False
    assert read_shadow_summary(path=write(tmp_path, row), now=NOW)["status"] == "INVALID"
    row = profile(generated_at=(NOW + timedelta(days=1)).isoformat())
    assert read_shadow_summary(path=write(tmp_path, row), now=NOW)["status"] == "INVALID"


def test_corrupt_json_fails_closed(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text('{"training_environment": "PAPER",', encoding="utf-8")
    assert read_shadow_summary(path=p, now=NOW)["status"] == "INVALID"


def test_mobile_control_center_has_real_refresh_and_source_links():
    assert 'id="paper-control-center"' in SCRIPT
    assert 'id="shadow-refresh"' in SCRIPT
    assert 'id="shadow-source"' in SCRIPT
    assert "addEventListener('click',refreshDemo)" in SCRIPT
    assert "renderShadow" in SCRIPT
    assert "demo-status" in SCRIPT


def test_api_reads_latest_profile_without_real_order_access(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "false")
    monkeypatch.setenv("ATLAS_DEMO_STATUS", str(tmp_path / "missing-status.json"))
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "paper-ledger.json"))
    (tmp_path / "paper-ledger.json").write_text(
        '{"open_positions":[],"closed_trades":[]}', encoding="utf-8"
    )
    current_profile = profile(generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setenv("ATLAS_COUNCIL_PROFILE", str(write(tmp_path, current_profile)))
    client = TestClient(app)
    response = client.get("/dashboard/demo-status")
    assert response.status_code == 200
    data = response.json()
    assert data["shadow_learning"]["status"] == "FRESH"
    assert data["shadow_learning"]["settled_paper_examples"] == 10
    assert data["summary"]["closed_trades"] == 0
    assert data["automatic_live_activation"] is False
    assert data["shadow_learning"]["broker_execution_allowed"] is False
    assert "agents" not in data["shadow_learning"]
    assert client.post("/mt5/test-order", json={}).status_code == 403
    assert "shadow_learning" not in client.get("/dashboard/trader-view").json()
