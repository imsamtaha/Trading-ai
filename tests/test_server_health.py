import json
from datetime import datetime, timezone
from app.runtime_control.server_health import read_server_health

def test_missing_monitor_is_not_reported_healthy(tmp_path):
    assert read_server_health(tmp_path / "absent.json")["state"] == "UNAVAILABLE"

def test_old_heartbeat_is_stale(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z", "components": {}}))
    assert read_server_health(path, now=1790813101)["state"] == "STALE"

def test_fresh_monitor_filters_extra_secret_fields(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z",
        "password": "PRIVATE", "components": {"backend": {"state": "HEALTHY", "secret": "PRIVATE"},
        "mt5": {"state": "HEALTHY", "open_positions": 2}}, "actions": ["STARTED ATLAS Web Frontend"]}))
    result = read_server_health(path, now=1790812860)
    assert result["state"] == "ACTIVE"
    assert result["components"]["backend"] == {"state": "HEALTHY"}
    assert result["components"]["mt5"]["open_positions"] == 2
    assert "PRIVATE" not in json.dumps(result)

def test_corrupt_monitor_is_unavailable(tmp_path):
    path = tmp_path / "status.json"
    path.write_text("broken")
    assert read_server_health(path)["state"] == "UNAVAILABLE"

def test_future_heartbeat_is_not_active(tmp_path):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"checked_at_utc": "2026-10-01T00:00:00Z", "components": {}}))
    assert read_server_health(path, now=1790810000)["state"] == "STALE"

