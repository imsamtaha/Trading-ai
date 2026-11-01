"""ATLAS manager can inspect real legacy journals but never mark missing risk evidence as PASS."""
import json

from scripts.atlas_ops_manager import assess, main


def _legacy():
    return {
        "timestamp": "2026-10-29T03:34:00Z",
        "snapshot_id": "snapshot-1", "realized_direction": "NEUTRAL",
        "opinions": [{"agent": "Nova", "decision": "NEUTRAL", "confidence": 0.8}],
        "execution_environment": "paper", "broker_execution_allowed": False,
    }


def test_manager_legacy_without_canonical_source_stays_blocked():
    result = assess([_legacy()], "false", "legacy")
    assert result["operations_status"] == "BLOCKED"
    assert result["gates"]["paper_evidence"] == "UNVERIFIED"
    assert result["gates"]["runtime_health"] == "UNVERIFIED"
    assert result["runtime_verified"] is False


def test_manager_rejects_broker_write_evidence():
    row = _legacy()
    row["broker_execution_allowed"] = True
    result = assess([row], "false", "legacy")
    assert result["operations_status"] == "BLOCKED"
    assert result["audit"]["status"] == "FAIL"


def test_manager_cli_real_legacy_schema_is_readonly(tmp_path, capsys, monkeypatch):
    path = tmp_path / "council_training.jsonl"
    original = json.dumps(_legacy()) + "\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    assert main([str(path), "--journal-format", "legacy"]) == 2
    assert path.read_text(encoding="utf-8") == original
    output = json.loads(capsys.readouterr().out)
    assert output["audit"]["legacy_records"] == 1


def test_manager_missing_live_flag_is_blocked_even_with_canonical_source():
    row = {
        "decision_id": "d1", "timestamp": "2026-10-29T03:34:00Z",
        "votes": [{"agent": "Nova", "direction": "NEUTRAL", "timestamp": "2026-10-29T03:34:00Z", "reason": "no edge"}],
        "risk": {"veto": False}, "outcome": {"opened": False},
    }
    assert assess([row], None)["operations_status"] == "BLOCKED"
