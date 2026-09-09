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
