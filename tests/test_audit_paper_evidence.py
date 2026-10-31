"""Regression tests for the read-only Paper evidence auditor."""
from scripts.audit_paper_evidence import audit


def complete_row(key="a", veto=False, opened=False):
    return {
        "decision_id": key,
        "timestamp": "2026-10-29T03:34:00Z",
        "votes": [{"agent": "Nova", "direction": "NEUTRAL", "timestamp": "2026-10-29T03:34:00Z", "reason": "no edge"}],
        "risk": {"veto": veto},
        "outcome": {"opened": opened},
    }


def test_complete_record_passes_schema_gates():
    assert audit([complete_row()])["status"] == "PASS"


def test_duplicate_decision_is_rejected():
    result = audit([complete_row(), complete_row()])
    assert result["status"] == "FAIL"
    assert any(f["gate"] == "unique_decisions" for f in result["findings"])


def test_risk_veto_cannot_open_position():
    result = audit([complete_row(veto=True, opened=True)])
    assert result["status"] == "FAIL"
    assert any(f["gate"] == "risk_veto" for f in result["findings"])


def test_missing_evidence_is_unverified_not_success():
    result = audit([{"decision_id": "a"}])
    assert result["status"] == "UNVERIFIED"


def test_incomplete_vote_provenance_is_unverified():
    row = complete_row()
    row["votes"] = [{"agent": "Nova", "direction": "NEUTRAL"}]
    assert audit([row])["status"] == "UNVERIFIED"
