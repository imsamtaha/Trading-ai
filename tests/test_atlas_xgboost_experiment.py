import json
import subprocess
import sys

import pytest

from app.intelligence.council_training import PaperTrainingExample
from app.intelligence.xgboost_experiment import evaluate_paper_examples, prepare_snapshot_groups


def _examples(count=60):
    return [
        PaperTrainingExample(
            snapshot_id=f"paper-{i}",
            realized_direction="BUY" if i % 2 == 0 else "SELL",
            opinions=(
                {"agent": "technical", "decision": "BUY", "confidence": 0.55 + (i % 4) / 10},
                {"agent": "news", "decision": "SELL", "confidence": 0.45 + (i % 3) / 10},
            ),
        )
        for i in range(count)
    ]


def test_preparation_preserves_snapshot_groups_and_binary_correctness():
    groups = prepare_snapshot_groups(_examples(2))
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert [label for _, label in groups[0]] == [1, 0]
    assert [label for _, label in groups[1]] == [0, 1]


def test_rejects_duplicate_snapshot_instead_of_leaking_across_time():
    examples = _examples(2)
    with pytest.raises(ValueError, match="Duplicate snapshot"):
        prepare_snapshot_groups([examples[0], examples[0]])


def test_rejects_invalid_confidence_and_malformed_opinions():
    original = _examples(1)[0]
    invalid = PaperTrainingExample(
        snapshot_id="bad",
        realized_direction="BUY",
        opinions=({"agent": "technical", "decision": "BUY", "confidence": float("nan")},),
    )
    with pytest.raises(ValueError, match="finite"):
        prepare_snapshot_groups([invalid])
    repeated = PaperTrainingExample(
        snapshot_id="bad2", realized_direction="BUY", opinions=original.opinions[:1] * 2
    )
    with pytest.raises(ValueError, match="unique"):
        prepare_snapshot_groups([repeated])


def test_rejects_insufficient_settled_evidence():
    with pytest.raises(ValueError, match="Insufficient"):
        evaluate_paper_examples(_examples(29))


def test_report_is_research_only_and_does_not_modify_council_profiles():
    pytest.importorskip("xgboost")
    pytest.importorskip("sklearn")
    report = evaluate_paper_examples(_examples(60))
    assert report["status"] == "EVALUATION_COMPLETE"
    assert report["approval"] == "RESEARCH_ONLY"
    assert report["train_snapshots"] == 48
    assert report["test_snapshots"] == 12
    assert report["train_opinions"] == 96
    assert report["test_opinions"] == 24
    assert report["council_weights_modified"] is False
    assert report["broker_execution_allowed"] is False
    assert report["model_persisted"] is False
    assert 0 <= report["metrics"]["xgboost_brier"] <= 1
    assert report["quality_gate"] in {"OBSERVATIONAL_IMPROVEMENT", "NO_OBSERVED_IMPROVEMENT"}


def test_cli_fails_closed_on_missing_training_journal(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_atlas_xgboost.py", "--journal", str(tmp_path / "missing.jsonl")],
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "BLOCKED"
    assert json.loads(result.stdout)["broker_execution_allowed"] is False
