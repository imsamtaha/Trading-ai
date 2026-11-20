"""Operations Manager stays read-only and fail-closed."""
import json

from scripts.atlas_ops_manager import assess, main
from test_audit_paper_evidence import complete_row


def test_ops_reports_safe_paper_schema_only_not_live_ready():
    report = assess([complete_row()], "false")
    assert report["operations_status"] == "PAPER_SCHEMA_CHECK_ONLY"
    assert report["runtime_verified"] is False
    assert report["auto_remediation_executed"] is False


def test_ops_missing_flag_is_blocked():
    report = assess([complete_row()], None)
    assert report["operations_status"] == "BLOCKED"
    assert report["gates"]["live_disabled_environment_flag"] == "UNVERIFIED"


def test_ops_true_flag_is_blocked():
    report = assess([complete_row()], "true")
    assert report["operations_status"] == "BLOCKED"
    assert report["gates"]["live_disabled_environment_flag"] == "FAIL"


def test_ops_invalid_evidence_stays_blocked():
    assert assess([], "false")["operations_status"] == "BLOCKED"


def test_ops_cli_reads_export_and_leaves_it_unchanged(tmp_path, monkeypatch, capsys):
    journal = tmp_path / "paper.jsonl"
    initial = json.dumps(complete_row()) + "\n"
    journal.write_text(initial, encoding="utf-8")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    assert main([str(journal)]) == 0
    assert journal.read_text(encoding="utf-8") == initial
    assert json.loads(capsys.readouterr().out)["mode"] == "READ_ONLY_PAPER"
