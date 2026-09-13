from pathlib import Path

from app.intelligence.journal import SignalJournal


def test_signal_journal_verify_reports_malformed_line(tmp_path: Path):
    path = tmp_path / "signals.jsonl"
    path.write_text(
        '{"status":"NO_TRADE"}\n'
        '{"status":\n'
        '{"status":"ERROR"}\n',
        encoding="utf-8",
    )

    report = SignalJournal(str(path)).verify()

    assert report == {
        "status": "CORRUPT",
        "records": 2,
        "malformed_records": 1,
        "malformed_lines": [2],
    }


def test_signal_journal_verify_accepts_appended_records(tmp_path: Path):
    journal = SignalJournal(str(tmp_path / "signals.jsonl"))
    journal.append({"symbol": "EURUSD", "status": "NO_TRADE"})

    assert journal.verify() == {
        "status": "OK",
        "records": 1,
        "malformed_records": 0,
        "malformed_lines": [],
    }
