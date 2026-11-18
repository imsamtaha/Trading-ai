"""Resource-safe scheduled PAPER research: no expensive imports under RAM pressure."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts import atlas_research_runner as runner


def fixture_paths(tmp_path):
    root = tmp_path / "research"
    code = root / "training-src" / "atlas_training" / "council_sklearn_research.py"
    code.parent.mkdir(parents=True)
    code.write_text("# research-only test fixture\n")
    journal = tmp_path / "paper" / "atlas_council_training.jsonl"
    journal.parent.mkdir(parents=True)
    journal.write_text('{"snapshot_id":"p1"}\n')
    db = root / "mlflow.db"
    db.write_bytes(b"fake-sqlite")
    return root, journal


def test_low_ram_defers_before_running_sklearn_or_mlflow(tmp_path, monkeypatch):
    root, journal = fixture_paths(tmp_path)
    monkeypatch.setattr(runner, "available_memory_mb", lambda: 120)
    def should_not_run(*args, **kwargs):
        raise AssertionError("must not import or execute research under low RAM")
    monkeypatch.setattr(runner.subprocess, "run", should_not_run)
    assert runner.run_research(root=root, journal=journal) == 3
    result = json.loads((root / "evidence" / "scheduler-status.json").read_text())
    assert result["status"] == "DEFERRED_LOW_MEMORY"
    assert result["required_mb"] == 1200
    assert result["active_council_weights_changed"] is False
    assert result["broker_execution_allowed"] is False


def test_missing_journal_fails_closed(tmp_path):
    root = tmp_path / "missing"
    assert runner.run_research(root=root, journal=tmp_path / "absent.jsonl") == 2
    status = json.loads((root / "evidence" / "scheduler-status.json").read_text())
    assert status["status"] == "FAILED_MISSING_INPUTS"


def test_reports_success_only_after_mlflow_evidence_provenance(tmp_path, monkeypatch):
    root, journal = fixture_paths(tmp_path)
    digest = hashlib.sha256(journal.read_bytes()).hexdigest()
    monkeypatch.setattr(runner, "available_memory_mb", lambda: 3000)

    def fake_run(args, **kwargs):
        assert "--mlflow-uri" in args
        assert "sqlite:///" in args[-1]
        assert kwargs["env"]["ATLAS_LIVE_TRADING"] == "false"
        assert kwargs["env"]["ATLAS_DASHBOARD_ONLY"] == "true"
        report = root / "evidence" / "council-agent-scores.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps({
            "source_sha256": digest,
            "active_council_weights_changed": False,
            "broker_execution_allowed": False,
            "mlflow_run_id": "run-research-test",
            "status": "HOLD_BASELINE",
        }))
        return subprocess.CompletedProcess(args, 0, "pass", "")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run_research(root=root, journal=journal) == 0
    status = json.loads((root / "evidence" / "scheduler-status.json").read_text())
    assert status["status"] == "SUCCESS"
    assert status["mlflow_run_id"] == "run-research-test"
    assert status["source_sha256"] == digest


def test_no_mlflow_id_fails_even_when_process_exit_zero(tmp_path, monkeypatch):
    root, journal = fixture_paths(tmp_path)
    monkeypatch.setattr(runner, "available_memory_mb", lambda: 2000)
    def fake_run(args, **kwargs):
        (root / "evidence" / "council-agent-scores.json").write_text(
            json.dumps({
                "source_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
                "active_council_weights_changed": False,
                "broker_execution_allowed": False,
                "status": "HOLD_BASELINE",
            }))
        return subprocess.CompletedProcess(args, 0, "pass", "")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run_research(root=root, journal=journal) == 2
    state = json.loads((root / "evidence" / "scheduler-status.json").read_text())
    assert state["status"] == "FAILED_UNVERIFIED_EVIDENCE"


def test_unavailable_memory_fails_closed(tmp_path, monkeypatch):
    root, journal = fixture_paths(tmp_path)
    def fail():
        raise OSError("memory unavailable")
    monkeypatch.setattr(runner, "available_memory_mb", fail)
    assert runner.run_research(root=root, journal=journal) == 2
    assert json.loads((root / "evidence" / "scheduler-status.json").read_text())["status"] == "FAILED_MEMORY_CHECK"
