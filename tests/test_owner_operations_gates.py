"""Read-only owner operations evidence and release gating regression tests."""
from app.owner_dashboard import audit_paper_rows, release_readiness


def test_audit_flags_missing_duplicate_and_risk_veto():
    data = {"decision_evidence": [
        {"decision_id": "D1", "decision": "BUY", "risk_veto": True,
         "snapshot_id": "S1", "outcome": "LOSS", "council_votes": [{"agent": "risk"}]},
        {"decision_id": "D1", "decision": "HOLD"},
        {"decision": "SELL", "risk_veto": False},
    ]}
    flags = audit_paper_rows(data)
    codes = [flag["code"] for flag in flags]
    assert "RISK_VETO_ACTION_CONFLICT" in codes
    assert "DUPLICATE_DECISION_ID" in codes
    assert "MISSING_DECISION_ID" in codes
    assert "MISSING_PROVENANCE" in codes
    assert "MISSING_OUTCOME" in codes
    assert "MISSING_VOTES" in codes


def test_release_gates_fail_closed_for_absent_validation():
    data = {"decision_evidence": [{"decision_id": "D1"}],
            "release_validation": {}}
    result = release_readiness(data, "VERIFIED", [])
    assert result["status"] == "BLOCKED"
    assert result["checks"]["windows_verified"] is False
    assert result["checks"]["ci"] is False


def test_stale_snapshot_blocks_even_with_other_checks():
    data = {"decision_evidence": [{"decision_id": "D1"}],
            "release_validation": {
                "windows_verified": True,
                "ledger_readback": "PASS",
                "pr_103_test_status": "PASS",
                "ci_status": "PASS",
                "issue_82_status": "CLOSED",
            }}
    result = release_readiness(data, "STALE", [])
    assert result["status"] == "BLOCKED"
    assert result["checks"]["signed_snapshot_fresh"] is False


def test_evidence_flags_block_release():
    data = {"decision_evidence": [{"decision_id": "D1"}],
            "release_validation": {
                "windows_verified": True, "ledger_readback": "PASS",
                "pr_103_test_status": "PASS", "ci_status": "PASS",
                "issue_82_status": "CLOSED",
            }}
    assert release_readiness(data, "VERIFIED",
                             [{"code": "MISSING_OUTCOME"}])["status"] == "BLOCKED"
