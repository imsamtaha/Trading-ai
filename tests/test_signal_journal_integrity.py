from pathlib import Path

import pytest

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


def test_signal_journal_flushes_record_to_disk_before_fsync(tmp_path: Path, monkeypatch):
    path = tmp_path / "signals.jsonl"
    observed_contents: list[str] = []

    def observe_fsync(_file_descriptor: int) -> None:
        observed_contents.append(path.read_text(encoding="utf-8"))

    monkeypatch.setattr("app.intelligence.journal.os.fsync", observe_fsync)

    SignalJournal(str(path)).append({"symbol": "EURUSD", "status": "NO_TRADE"})

    assert len(observed_contents) == 1
    assert '"symbol":"EURUSD"' in observed_contents[0]
    assert observed_contents[0].endswith("\n")


def test_signal_journal_verify_reports_invalid_utf8_line(tmp_path: Path):
    path = tmp_path / "signals.jsonl"
    path.write_bytes(b'{"status":"NO_TRADE"}\n{"reason":"\xff"}\n')

    assert SignalJournal(str(path)).verify() == {
        "status": "CORRUPT",
        "records": 1,
        "malformed_records": 1,
        "malformed_lines": [2],
    }


@pytest.mark.parametrize("value", ["null", "[]", '"text"', "42", "true"])
def test_signal_journal_verify_rejects_non_object_json(tmp_path: Path, value: str):
    path = tmp_path / "signals.jsonl"
    path.write_text(value + "\n", encoding="utf-8")

    assert SignalJournal(str(path)).verify() == {
        "status": "CORRUPT",
        "records": 0,
        "malformed_records": 1,
        "malformed_lines": [1],
    }


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_signal_journal_verify_rejects_non_json_numeric_constants(
    tmp_path: Path,
    constant: str,
):
    path = tmp_path / "signals.jsonl"
    path.write_text(f'{{"confidence":{constant}}}\n', encoding="utf-8")

    assert SignalJournal(str(path)).verify() == {
        "status": "CORRUPT",
        "records": 0,
        "malformed_records": 1,
        "malformed_lines": [1],
    }


def test_signal_journal_append_rejects_nan_without_creating_record(tmp_path: Path):
    path = tmp_path / "signals.jsonl"

    with pytest.raises(ValueError, match="Out of range float values"):
        SignalJournal(str(path)).append({"confidence": float("nan")})

    assert not path.exists()


def test_signal_journal_construction_is_read_only(tmp_path: Path):
    path = tmp_path / "missing" / "signals.jsonl"

    SignalJournal(str(path))

    assert not path.parent.exists()
