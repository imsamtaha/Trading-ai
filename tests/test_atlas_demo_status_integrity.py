from pathlib import Path

from scripts.atlas_demo_status import main


def _write_empty_ledger(path: Path) -> None:
    path.write_text(
        '{"open_positions": [], "closed_trades": []}',
        encoding="utf-8",
    )


def test_demo_status_returns_nonzero_for_corrupt_signal_journal(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    ledger_path = tmp_path / "ledger.json"
    _write_empty_ledger(ledger_path)
    journal_path = tmp_path / "signals.jsonl"
    journal_path.write_bytes(b'{"status":"NO_TRADE"}\n{"reason":"\xff"}\n')
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(ledger_path))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(journal_path))

    assert main() == 3
    output = capsys.readouterr().out
    assert '"signal_journal"' in output
    assert '"status": "CORRUPT"' in output
    assert '"malformed_lines": [' in output


def test_demo_status_rejects_missing_signal_journal(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    ledger_path = tmp_path / "ledger.json"
    _write_empty_ledger(ledger_path)
    journal_path = tmp_path / "missing" / "signals.jsonl"
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(ledger_path))
    monkeypatch.setenv("ATLAS_SIGNAL_JOURNAL", str(journal_path))

    assert main() == 4
    output = capsys.readouterr().out
    assert '"exists": false' in output
    assert '"status": "MISSING"' in output
    assert not journal_path.parent.exists()
