import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("atlas_watchdog", Path(__file__).parents[1] / "ops" / "atlas_windows_watchdog.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

def cycle(directory, backend=True, frontend=True, public=False, now=1000):
    def health(url):
        if "8012" in url: return backend
        if "8011" in url: return frontend
        return public
    with patch.object(w, "http_health", side_effect=health), patch.object(w, "check_mt5", return_value={"state": "ALGO_DISABLED"}), patch.object(w, "powershell", return_value="Running"), patch.object(w.time, "time", return_value=now):
        return w.check_cycle(directory)

def test_public_outage_recovers_tunnel_after_three_failures(tmp_path):
    assert cycle(tmp_path)["actions"] == []
    assert cycle(tmp_path)["actions"] == []
    status = cycle(tmp_path)
    assert status["actions"] == ["RESTARTED ATLAS Tunnel Recovery"]
    assert cycle(tmp_path, now=1001)["actions"] == []

def test_local_frontend_failure_does_not_restart_tunnel(tmp_path):
    for _ in range(4):
        status = cycle(tmp_path, frontend=False)
        assert "RESTARTED ATLAS Tunnel Recovery" not in status["actions"]

def test_recovered_public_route_resets_recovery_budget(tmp_path):
    for _ in range(3): cycle(tmp_path)
    status = cycle(tmp_path, public=True)
    assert status["actions"] == []
    state = json.loads((tmp_path / "recovery-state.json").read_text())
    assert state["tunnel"]["attempts"] == 0

def test_maintenance_suppresses_service_restarts(tmp_path):
    (tmp_path / "maintenance.json").write_text(json.dumps({"expires_at": 1100}))
    for _ in range(4):
        assert cycle(tmp_path, frontend=False)["actions"] == []


def test_watchdog_exits_before_probing_legacy_services(monkeypatch, capsys):
    monkeypatch.delenv("ATLAS_BROKER_PROVIDER", raising=False)
    monkeypatch.delenv("ATLAS_MT5_CONNECTIONS_PAUSED", raising=False)
    monkeypatch.setattr(w.sys, "argv", ["atlas_windows_watchdog.py", "--mt5-probe"])
    with patch.object(w, "load_dotenv"), patch.object(w, "mt5_probe") as probe:
        w.main()
    probe.assert_not_called()
    assert json.loads(capsys.readouterr().out)["state"] == "PAUSED"
