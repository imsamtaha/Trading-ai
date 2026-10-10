import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location("paper_watchdog", Path(__file__).parents[1] / "ops" / "atlas_windows_watchdog.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


@pytest.fixture
def server_dir(tmp_path):
    directory = tmp_path / "server"
    directory.mkdir()
    return directory


def cycle(directory, task_state="Ready", now=1000, fail_start=False):
    def task(code):
        if code.startswith("(Get-ScheduledTask"):
            return task_state
        if code == "Start-ScheduledTask -TaskName 'ATLAS Paper Monitor'":
            if fail_start:
                raise RuntimeError("WINDOWS_TASK_OPERATION_FAILED")
            return ""
        raise AssertionError("Unexpected task operation: " + code)
    with patch.object(w, "http_health", return_value=True), patch.object(w, "check_mt5", return_value={"state": "ALGO_DISABLED"}), patch.object(w, "powershell", side_effect=task), patch.object(w.time, "time", return_value=now):
        return w.check_cycle(directory)


def test_stopped_paper_task_starts_after_three_observations(server_dir):
    for _ in range(2):
        assert cycle(server_dir)["actions"] == []
    result = cycle(server_dir)
    assert result["actions"] == ["STARTED ATLAS Paper Monitor"]
    assert result["components"]["paper"]["state"] == "START_REQUESTED"
    assert cycle(server_dir, now=1001)["actions"] == []


def test_persistently_stopped_paper_task_has_bounded_start_budget(server_dir):
    starts = []
    for now in range(1000, 10000, 400):
        result = cycle(server_dir, now=now)
        starts.extend(result["actions"])
    assert starts == ["STARTED ATLAS Paper Monitor"] * 5
    assert result["components"]["paper"]["state"] == "RECOVERY_EXHAUSTED"


def test_stale_running_paper_task_is_reported_without_restart(server_dir):
    for now in range(1000, 4000, 400):
        result = cycle(server_dir, task_state="Running", now=now)
        assert result["actions"] == []
        assert result["components"]["paper"]["state"] == "HEARTBEAT_UNAVAILABLE"


def test_disabled_paper_task_is_not_enabled_or_started(server_dir):
    for _ in range(4):
        result = cycle(server_dir, task_state="Disabled")
        assert result["actions"] == []
        assert result["components"]["paper"]["state"] == "TASK_REQUIRES_ATTENTION"


def test_paper_recovery_is_suppressed_during_maintenance(server_dir):
    (server_dir / "maintenance.json").write_text(json.dumps({"expires_at": 1100}))
    for _ in range(4):
        assert cycle(server_dir)["actions"] == []
    state = json.loads((server_dir / "recovery-state.json").read_text())
    assert state["paper"]["failures"] == 0


def test_fresh_running_paper_task_resets_start_budget(server_dir):
    for _ in range(3): cycle(server_dir)
    log = server_dir.parent / "paper" / "paper-monitor.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text("paper cycle")
    os.utime(log, (1000, 1000))
    result = cycle(server_dir, task_state="Running")
    assert result["components"]["paper"]["state"] == "HEALTHY"
    state = json.loads((server_dir / "recovery-state.json").read_text())
    assert state["paper"]["starts"] == 0


def test_failed_paper_start_consumes_budget_and_is_reported(server_dir):
    for _ in range(3): result = cycle(server_dir, fail_start=True)
    assert result["actions"] == []
    assert result["components"]["paper"]["state"] == "TASK_OPERATION_FAILED"
    state = json.loads((server_dir / "recovery-state.json").read_text())
    assert state["paper"]["starts"] == 1


def test_log_from_before_recovery_does_not_reset_start_budget(server_dir):
    log = server_dir.parent / "paper" / "paper-monitor.log"
    log.parent.mkdir()
    log.write_text("old cycle")
    os.utime(log, (990, 990))
    for _ in range(3): cycle(server_dir)
    result = cycle(server_dir, task_state="Running", now=1001)
    assert result["components"]["paper"]["state"] == "HEARTBEAT_UNAVAILABLE"
    state = json.loads((server_dir / "recovery-state.json").read_text())
    assert state["paper"]["starts"] == 1


def test_recent_persistence_error_marks_running_paper_degraded(server_dir):
    paper_dir = server_dir.parent / "paper"
    paper_dir.mkdir()
    log = paper_dir / "paper-monitor.log"
    log.write_text(
        "{'timestamp': '1970-01-01T00:16:40+00:00', "
        "'status': 'MT5_ERROR', "
        "'reason': 'Cannot persist demo ledger: WinError 5'}\n"
    )
    os.utime(log, (1000, 1000))
    ledger = paper_dir / "atlas_demo_ledger.json"
    ledger.write_text('{"open_positions": [], "closed_trades": []}')
    os.utime(ledger, (900, 900))
    result = cycle(server_dir, task_state="Running", now=1000)
    assert result["components"]["paper"]["state"] == "LEDGER_PERSISTENCE_FAILED"
    assert result["actions"] == []
    assert result["components"]["paper"]["last_ledger_error_utc"] == "1970-01-01T00:16:40Z"

    # A stopped task with an unresolved persistence fault must not auto-restart.
    for now in range(1001, 1400, 100):
        result = cycle(server_dir, task_state="Ready", now=now)
        assert result["components"]["paper"]["state"] == "LEDGER_PERSISTENCE_FAILED"
        assert result["actions"] == []

    # A verified more recent durable ledger update clears the failure.
    ledger.write_text('{"open_positions": [], "closed_trades": []}')
    os.utime(ledger, (1400, 1400))
    os.utime(log, (1401, 1401))
    result = cycle(server_dir, task_state="Running", now=1401)
    assert result["components"]["paper"]["state"] == "HEALTHY"
    state = json.loads((server_dir / "recovery-state.json").read_text())
    assert "ledger_failure_at" not in state["paper"]
