import os
from pathlib import Path

import pytest

from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError


def _trade_kwargs():
    return {
        "symbol": "EURUSD",
        "direction": "LONG",
        "entry": 1.1000,
        "stop_loss": 1.0980,
        "take_profit": 1.1040,
        "position_size": 5000,
        "risk": {"actual_risk_amount": 10.0, "risk_percent": 0.1, "risk_reward": 2.0},
        "strategy": "CONTINUATION_5M",
        "confidence": 75.0,
        "timeframe": "5m",
        "decision": {"decision": "BUY", "risk_level": "LOW"},
    }


def test_paper_ledger_persists_and_closes_take_profit(tmp_path: Path):
    ledger_path = tmp_path / "atlas_demo.json"
    ledger = MT5PaperLedger(str(ledger_path), max_open_positions=2)

    opened = ledger.open_trade(**_trade_kwargs())

    assert opened["status"] == "OPEN"
    assert ledger.summary() == {"open_positions": 1, "closed_trades": 0, "recorded_trades": 1}

    closed = ledger.close_due_positions("EURUSD", bid=1.1042, ask=1.1043)

    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "TAKE_PROFIT"
    assert closed[0]["r_multiple"] > 1.9
    assert ledger.summary() == {"open_positions": 0, "closed_trades": 1, "recorded_trades": 1}
    assert MT5PaperLedger(str(ledger_path)).closed_trades()[0]["id"] == opened["id"]
    assert MT5PaperLedger(str(ledger_path)).last_closed_trade("eurusd")["id"] == opened["id"]


def test_paper_ledger_blocks_duplicate_symbol(tmp_path: Path):
    ledger = MT5PaperLedger(str(tmp_path / "atlas_demo.json"))
    ledger.open_trade(**_trade_kwargs())

    with pytest.raises(PaperLedgerError, match="already exists"):
        ledger.open_trade(**_trade_kwargs())


def test_multiple_ledger_instances_preserve_each_others_trades(tmp_path: Path):
    ledger_path = tmp_path / "atlas_demo.json"
    first = MT5PaperLedger(str(ledger_path), max_open_positions=3)
    second = MT5PaperLedger(str(ledger_path), max_open_positions=3)

    first.open_trade(**_trade_kwargs())

    xau_trade = {
        **_trade_kwargs(),
        "symbol": "XAUUSD",
        "entry": 2000.0,
        "stop_loss": 1990.0,
        "take_profit": 2020.0,
    }
    second.open_trade(**xau_trade)

    reloaded = MT5PaperLedger(str(ledger_path), max_open_positions=3)
    assert {position["symbol"] for position in reloaded.open_positions()} == {
        "EURUSD",
        "XAUUSD",
    }
    assert reloaded.summary()["recorded_trades"] == 2


@pytest.mark.parametrize("open_limit", [5, 10])
def test_paper_ledger_caps_open_positions(tmp_path: Path, open_limit: int):
    ledger = MT5PaperLedger(
        str(tmp_path / "atlas_demo.json"),
        max_open_positions=open_limit,
        max_daily_entries=50,
    )

    for index in range(open_limit):
        ledger.open_trade(**{**_trade_kwargs(), "symbol": f"TEST{index}"})

    with pytest.raises(PaperLedgerError, match="Maximum open paper positions reached"):
        ledger.open_trade(**{**_trade_kwargs(), "symbol": "TEST_LIMIT"})


@pytest.mark.parametrize("daily_limit", [50, 100, 150])
def test_paper_ledger_caps_daily_entries(tmp_path: Path, daily_limit: int):
    ledger = MT5PaperLedger(
        str(tmp_path / "atlas_demo.json"),
        max_open_positions=5,
        max_daily_entries=daily_limit,
    )

    for _ in range(daily_limit):
        ledger.open_trade(**_trade_kwargs())
        closed = ledger.close_due_positions("EURUSD", bid=1.1042, ask=1.1043)
        assert len(closed) == 1

    with pytest.raises(PaperLedgerError, match="Maximum daily paper entries reached"):
        ledger.open_trade(**_trade_kwargs())


@pytest.mark.parametrize(
    ("open_limit", "daily_limit"),
    [(0, 50), (11, 50), (5, 0), (5, 151)],
)
def test_paper_ledger_rejects_limits_above_safety_ceiling(
    tmp_path: Path,
    open_limit: int,
    daily_limit: int,
):
    with pytest.raises(PaperLedgerError):
        MT5PaperLedger(
            str(tmp_path / "atlas_demo.json"),
            max_open_positions=open_limit,
            max_daily_entries=daily_limit,
        )

def test_paper_ledger_retries_transient_replace_lock_without_duplicates(tmp_path, monkeypatch):
    from app.paper_trading import mt5_ledger as module
    real_replace = Path.replace
    attempts = []
    def transient_replace(path, target):
        attempts.append(path)
        if len(attempts) <= 2:
            raise PermissionError("Transient Windows sharing lock")
        return real_replace(path, target)
    monkeypatch.setattr(Path, "replace", transient_replace)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    ledger = MT5PaperLedger(str(tmp_path / "retry.json"))
    ledger.open_trade(**_trade_kwargs())
    assert len(attempts) == 3
    assert MT5PaperLedger(str(tmp_path / "retry.json")).summary()["recorded_trades"] == 1

def test_paper_ledger_persistent_replace_failure_preserves_original(tmp_path, monkeypatch):
    from app.paper_trading import mt5_ledger as module
    path = tmp_path / "retry.json"
    ledger = MT5PaperLedger(str(path))
    ledger.open_trade(**_trade_kwargs())
    original = path.read_bytes()
    attempts = []
    def locked(path, target):
        attempts.append(path)
        raise PermissionError("Persistent sharing lock")
    monkeypatch.setattr(Path, "replace", locked)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    def denied_fallback(*args):
        raise PermissionError("Persistent Windows sharing lock")
    monkeypatch.setattr(module, "_win_replace_existing", denied_fallback)
    with pytest.raises(PaperLedgerError, match="Cannot persist"):
        ledger.close_due_positions("EURUSD", bid=1.1042, ask=1.1043)
    assert len(attempts) == 6
    assert path.read_bytes() == original
    assert list(tmp_path.glob('retry.json.*.tmp')) == []

def test_category_limit_is_enforced_across_ledger_instances(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_CATEGORY_POSITION_LIMIT", "2")
    path = str(tmp_path / "category.json")
    first = MT5PaperLedger(path)
    second = MT5PaperLedger(path)
    for symbol in ["BITCOIN", "ETHEREUM"]:
        first.open_trade(**{**_trade_kwargs(), "symbol": symbol})
    with pytest.raises(PaperLedgerError, match="CRYPTO concentration"):
        second.open_trade(**{**_trade_kwargs(), "symbol": "SOLANA"})
    second.open_trade(**{**_trade_kwargs(), "symbol": "AAPL.O"})
    assert first.summary()["open_positions"] == 3


@pytest.mark.skipif(os.name != "nt", reason="Uses Windows ReplaceFileW")
def test_windows_atomic_replace_fallback_succeeds_when_movefile_denied(tmp_path, monkeypatch):
    from app.paper_trading import mt5_ledger as module

    path = tmp_path / "paper.json"
    ledger = MT5PaperLedger(str(path))
    ledger.open_trade(**_trade_kwargs())
    attempts = []
    def sharing_violation(*args):
        attempts.append(1)
        raise PermissionError("MoveFileEx target is held open")
    monkeypatch.setattr(Path, "replace", sharing_violation)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    closed = ledger.close_due_positions("EURUSD", bid=1.1042, ask=1.1043)
    assert len(attempts) == 6
    assert len(closed) == 1
    assert MT5PaperLedger(str(path)).summary()["closed_trades"] == 1
    assert not list(tmp_path.glob("paper.json.*.tmp"))
