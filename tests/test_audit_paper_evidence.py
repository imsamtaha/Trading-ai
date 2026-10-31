"""Regression tests for fail-closed, read-only PAPER evidence auditor."""
import json
import os

import pytest

from scripts.audit_paper_evidence import audit, main


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
    assert audit([{"decision_id": "a"}])["status"] == "UNVERIFIED"


def test_incomplete_vote_provenance_is_unverified():
    row = complete_row()
    row["votes"] = [{"agent": "Nova", "direction": "NEUTRAL"}]
    assert audit([row])["status"] == "UNVERIFIED"


@pytest.mark.parametrize("mutator", [
    lambda r: r.update(votes=[]),
    lambda r: r.update(votes="not-a-list"),
    lambda r: r.update(outcome={}),
    lambda r: r.update(risk={}),
    lambda r: r.update(timestamp=" "),
    lambda r: r["votes"][0].update(reason=" "),
    lambda r: r.update(outcome={"opened": 1}),
    lambda r: r.update(risk={"veto": "false"}),
])
def test_incomplete_records_never_pass(mutator):
    row = complete_row()
    mutator(row)
    assert audit([row])["status"] != "PASS"


@pytest.mark.parametrize("decision_id", [[], {}, 123, None, " "])
def test_malformed_decision_ids_fail_without_crashing(decision_id):
    assert audit([complete_row(decision_id)])["status"] == "FAIL"


def test_empty_journal_cannot_pass():
    assert audit([])["status"] == "UNVERIFIED"


def test_invalid_record_is_fail():
    assert audit([123])["status"] == "FAIL"


def test_whitespace_ids_are_normalized_for_duplicates():
    assert audit([complete_row(" a "), complete_row("a")])["status"] == "FAIL"


def test_cli_valid_journal_does_not_change_input(tmp_path, capsys):
    journal = tmp_path / "private.jsonl"
    content = json.dumps(complete_row()) + "\n"
    journal.write_text(content, encoding="utf-8")
    assert main([str(journal)]) == 0
    assert journal.read_text(encoding="utf-8") == content
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_cli_output_must_be_new(tmp_path):
    journal = tmp_path / "private.jsonl"
    journal.write_text(json.dumps(complete_row()), encoding="utf-8")
    output = tmp_path / "report.json"
    assert main([str(journal), "--output", str(output)]) == 0
    with pytest.raises(SystemExit) as exc:
        main([str(journal), "--output", str(output)])
    assert exc.value.code == 2


def test_cli_same_path_refuses_overwrite(tmp_path):
    journal = tmp_path / "private.jsonl"
    original = json.dumps(complete_row())
    journal.write_text(original, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([str(journal), "--output", str(journal)])
    assert exc.value.code == 2
    assert journal.read_text(encoding="utf-8") == original


def test_cli_hardlink_cannot_overwrite_input(tmp_path):
    journal = tmp_path / "private.jsonl"
    original = json.dumps(complete_row())
    journal.write_text(original, encoding="utf-8")
    alias = tmp_path / "alias.jsonl"
    try:
        os.link(journal, alias)
    except OSError:
        pytest.skip("Hardlinks unavailable on this file system")
    with pytest.raises(SystemExit) as exc:
        main([str(journal), "--output", str(alias)])
    assert exc.value.code == 2
    assert journal.read_text(encoding="utf-8") == original


def test_cli_empty_journal_exit_two(tmp_path):
    journal = tmp_path / "private.jsonl"
    journal.write_text("\n", encoding="utf-8")
    assert main([str(journal)]) == 2
