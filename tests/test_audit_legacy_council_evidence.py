"""Fail-closed regression cases for historical Council PAPER journal compatibility."""
import json

from scripts.audit_legacy_council_evidence import inspect_legacy, main


def legacy(snapshot="snapshot-1"):
    return {
        "timestamp": "2026-10-29T03:34:00Z",
        "snapshot_id": snapshot,
        "realized_direction": "NEUTRAL",
        "opinions": [{"agent": "Nova", "decision": "NEUTRAL", "confidence": 0.8}],
        "execution_environment": "paper",
        "broker_execution_allowed": False,
    }


def canonical(snapshot="snapshot-1"):
    return {
        "decision_id": "decision-1", "source_snapshot_id": snapshot,
        "timestamp": "2026-10-29T03:34:00Z",
        "votes": [{"agent": "Nova", "direction": "NEUTRAL", "timestamp": "2026-10-29T03:34:00Z", "reason": "no edge"}],
        "risk": {"veto": False}, "outcome": {"opened": False},
    }


def test_legacy_never_claims_outcome_without_independent_source():
    result = inspect_legacy([legacy()])
    assert result["status"] == "UNVERIFIED"
    assert result["canonical_decisions"] is None
    assert any(f["gate"] == "canonical_decision_outcome_source" for f in result["findings"])


def test_complete_independent_source_can_validate_schema_join():
    result = inspect_legacy([legacy()], [canonical()])
    assert result["status"] == "PASS"
    assert result["verified_joins"] == 1
    assert result["broker_write_executed"] is False


def test_canonical_veto_open_contradiction_is_fail():
    row = canonical()
    row["risk"]["veto"] = True
    row["outcome"]["opened"] = True
    assert inspect_legacy([legacy()], [row])["status"] == "FAIL"


def test_missing_canonical_vote_reason_never_passes():
    row = canonical()
    row["votes"][0].pop("reason")
    assert inspect_legacy([legacy()], [row])["status"] == "UNVERIFIED"


def test_canonical_vote_disagreement_never_passes():
    row = canonical()
    row["votes"][0]["direction"] = "BUY"
    assert inspect_legacy([legacy()], [row])["status"] == "UNVERIFIED"


def test_unmatched_snapshot_never_passes():
    assert inspect_legacy([legacy()], [canonical("unknown")])["status"] == "UNVERIFIED"


def test_duplicate_legacy_snapshots_fail():
    assert inspect_legacy([legacy(), legacy()])["status"] == "FAIL"


def test_broker_execution_true_fails():
    row = legacy()
    row["broker_execution_allowed"] = True
    assert inspect_legacy([row])["status"] == "FAIL"


def test_missing_broker_flag_is_unverified():
    row = legacy()
    row.pop("broker_execution_allowed")
    assert inspect_legacy([row])["status"] == "UNVERIFIED"


def test_empty_legacy_is_unverified():
    assert inspect_legacy([])["status"] == "UNVERIFIED"


def test_empty_opinions_are_unverified():
    row = legacy()
    row["opinions"] = []
    assert inspect_legacy([row])["status"] == "UNVERIFIED"


def test_empty_or_invalid_confidence_is_unverified():
    row = legacy()
    row["opinions"][0]["confidence"] = float("nan")
    assert inspect_legacy([row])["status"] == "UNVERIFIED"


def test_duplicate_canonical_ids_fail():
    assert inspect_legacy([legacy()], [canonical(), canonical()])["status"] == "FAIL"


def test_cli_real_legacy_shape_read_only(tmp_path, capsys):
    path = tmp_path / "training.jsonl"
    text = json.dumps(legacy()) + "\n"
    path.write_text(text, encoding="utf-8")
    assert main([str(path)]) == 2
    assert path.read_text(encoding="utf-8") == text
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "UNVERIFIED"
    assert output["mode"] == "READ_ONLY_PAPER_EVIDENCE"
