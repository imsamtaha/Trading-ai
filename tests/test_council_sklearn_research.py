import json
import math
import sys
from types import SimpleNamespace

import pytest

pytest.importorskip("sklearn")
from atlas_training.council_sklearn_research import (
    MIN_AGENT_SAMPLES, evaluate_paper_agents, log_to_mlflow, main,
)


def _journal(path, rows=100, *, duplicate=False, invalid=False):
    with path.open("w", encoding="utf-8") as f:
        for idx in range(rows):
            real = "BUY" if idx % 2 else "SELL"
            tech = real if idx % 4 else ("SELL" if real == "BUY" else "BUY")
            payload = {
                "snapshot_id": "same" if duplicate else f"paper-{idx:04d}",
                "realized_direction": real,
                "opinions": [
                    {"agent": "technical", "decision": tech, "confidence": 0.6 if idx % 3 else 0.8},
                    {"agent": "news", "decision": real if idx % 3 else "HOLD", "confidence": 0.7},
                ],
                "execution_environment": "LIVE" if invalid else "PAPER",
                "broker_execution_allowed": False,
            }
            f.write(json.dumps(payload) + "\n")
    return path


def test_insufficient_settled_samples_hold_baseline(tmp_path):
    report = evaluate_paper_agents(_journal(tmp_path / "training.jsonl", rows=30))
    assert report["status"] == "HOLD_BASELINE"
    assert report["unique_snapshots"] == 30
    assert set(report["agents"]) == {"technical", "news"}
    assert all(v["status"] == "HOLD_BASELINE" for v in report["agents"].values())
    assert all(v["candidate_weight"] is None for v in report["agents"].values())
    assert report["active_council_weights_changed"] is False
    assert report["live_trading_enabled"] is False


def test_chronological_validation_each_agent_independent(tmp_path):
    source = _journal(tmp_path / "training.jsonl", rows=110)
    report = evaluate_paper_agents(source)
    assert report["unique_snapshots"] == 110
    assert report["min_samples_per_agent"] == MIN_AGENT_SAMPLES
    for agent in ("news", "technical"):
        row = report["agents"][agent]
        assert row["samples"] == 110
        assert row["status"] in {"HOLD_BASELINE", "SHADOW_REVIEW"}
        assert row["baseline_weight"] == 1.0
        if row["status"] == "SHADOW_REVIEW":
            assert 0.5 <= row["candidate_weight"] <= 1.5
        else:
            assert row["candidate_weight"] is None
        assert row["metrics"]["train_examples"] == int(110 * 0.75)
        assert row["metrics"]["holdout_examples"] == 110 - int(110 * 0.75) - 1
        assert all(math.isfinite(v) for k, v in row["metrics"].items() if isinstance(v, float))
    assert report["broker_execution_allowed"] is False
    assert report["council_weight_activation"] is False
    assert report["automatic_promotion"] is False


def test_duplicate_snapshot_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="duplicate snapshot"):
        evaluate_paper_agents(_journal(tmp_path / "training.jsonl", rows=2, duplicate=True))


def test_live_training_record_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="PAPER"):
        evaluate_paper_agents(_journal(tmp_path / "training.jsonl", rows=2, invalid=True))


def test_missing_journal_does_not_claim_active_weights(tmp_path, capsys):
    code = main(["--journal", str(tmp_path / "absent.jsonl")])
    assert code == 2
    report = json.loads(capsys.readouterr().err)
    assert report["status"] == "HOLD_BASELINE"
    assert report["active_council_weights_changed"] is False


def test_min_sample_gate_cannot_be_lowered(tmp_path):
    source = _journal(tmp_path / "training.jsonl", rows=90)
    with pytest.raises(ValueError, match="cannot be reduced"):
        evaluate_paper_agents(source, min_samples=5)


def test_mlflow_logging_is_exclusively_evidence(monkeypatch, tmp_path):
    journal = _journal(tmp_path / "training.jsonl", rows=25)
    payload = evaluate_paper_agents(journal)
    calls = []
    class _Run:
        info = SimpleNamespace(run_id="shadow-run-1")
        def __enter__(self): return self
        def __exit__(self, *args): pass
    dummy = SimpleNamespace(
        set_tracking_uri=lambda x: calls.append(("uri", x)),
        set_experiment=lambda x: calls.append(("exp", x)),
        start_run=lambda **kw: (calls.append(("start", kw)), _Run())[1],
        log_params=lambda x: calls.append(("params", x)),
        log_metrics=lambda x: calls.append(("metrics", x)),
        log_dict=lambda payload, name: calls.append(("artifact", name)),
    )
    monkeypatch.setitem(sys.modules, "mlflow", dummy)
    assert log_to_mlflow(payload, uri="http://127.0.0.1:5000") == "shadow-run-1"
    assert ("artifact", "evidence/council-agent-scores.json") in calls
    assert not hasattr(dummy, "register_model")
    assert payload["automatic_promotion"] is False
