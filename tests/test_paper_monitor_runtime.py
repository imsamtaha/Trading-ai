import json
import os
import subprocess
import sys

import pytest

from app.monitor.runtime import monitor_lock, operational_log, runtime_path, write_health


def test_duplicate_process_blocked_then_released(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "paper.json"))
    child = [sys.executable, "-c",
             "from app.monitor.runtime import monitor_lock; "
             "guard=monitor_lock(); guard.__enter__()"]
    with monitor_lock():
        result = subprocess.run(child, capture_output=True, text=True)
        assert result.returncode != 0
        assert "MonitorAlreadyRunning" in result.stderr
    assert subprocess.run(child, capture_output=True).returncode == 0


def test_lock_released_after_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "paper.json"))
    with pytest.raises(RuntimeError):
        with monitor_lock():
            raise RuntimeError("crash")
    with monitor_lock():
        pass


def test_health_is_valid_and_preserves_ledger(monkeypatch, tmp_path):
    ledger = tmp_path / "paper.json"
    ledger.write_text('{"closed_trades": [1]}')
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(ledger))
    for status in ("CYCLE_STARTED", "CYCLE_COMPLETED", "CYCLE_FAILED"):
        write_health(status, events=2)
        health = json.loads(runtime_path(".health.json").read_text())
        assert health["status"] == status
        assert health["pid"] == os.getpid()
        assert health["broker_execution_allowed"] is False
    assert ledger.read_text() == '{"closed_trades": [1]}'


def test_operational_log_rotates_and_closes(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "paper.json"))
    with operational_log() as logger:
        handler = logger.handlers[-1]
        handler.maxBytes = 100
        logger.info("first event " + "x" * 60)
        logger.info("second event " + "x" * 60)
        assert runtime_path(".monitor.log.1").exists()
        assert "second event" in runtime_path(".monitor.log").read_text()
    assert handler not in logger.handlers
