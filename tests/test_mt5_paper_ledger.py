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


def test_paper_ledger_caps_open_positions_at_five(tmp_path: Path):
    ledger = MT5PaperLedger(
        str(tmp_path / "atlas_demo.json"),
        max_open_positions=5,
        max_daily_entries=15,
    )

    for index in range(5):
        ledger.open_trade(**{**_trade_kwargs(), "symbol": f"TEST{index}"})

    with pytest.raises(PaperLedgerError, match="Maximum open paper positions reached"):
        ledger.open_trade(**{**_trade_kwargs(), "symbol": "TEST5"})


def test_paper_ledger_caps_daily_entries_at_fifteen(tmp_path: Path):
    ledger = MT5PaperLedger(
        str(tmp_path / "atlas_demo.json"),
        max_open_positions=5,
        max_daily_entries=15,
    )

    for _ in range(15):
        ledger.open_trade(**_trade_kwargs())
        closed = ledger.close_due_positions("EURUSD", bid=1.1042, ask=1.1043)
        assert len(closed) == 1

    with pytest.raises(PaperLedgerError, match="Maximum daily paper entries reached"):
        ledger.open_trade(**_trade_kwargs())


@pytest.mark.parametrize(
    ("open_limit", "daily_limit"),
    [(0, 15), (6, 15), (5, 0), (5, 16)],
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
