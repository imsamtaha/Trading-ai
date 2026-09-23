import pytest

from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError


def _trade_kwargs():
    return {
        "symbol": "EURUSD",
        "direction": "LONG",
        "entry": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1100,
        "position_size": 1.0,
        "risk": {
            "actual_risk_amount": 50.0,
            "risk_percent": 0.5,
            "risk_reward": 2.0,
        },
        "strategy": "restart-contract",
        "confidence": 80.0,
        "timeframe": "5m",
        "decision": {"decision": "BUY"},
    }


def test_persisted_open_position_blocks_duplicate_after_restart(tmp_path):
    ledger_path = tmp_path / "atlas_demo_ledger.json"
    first_worker = MT5PaperLedger(path=str(ledger_path))
    first_worker.open_trade(**_trade_kwargs())

    restarted_worker = MT5PaperLedger(path=str(ledger_path))
    with pytest.raises(PaperLedgerError, match="already exists"):
        restarted_worker.open_trade(**_trade_kwargs())

    positions = restarted_worker.open_positions()
    assert len(positions) == 1
    assert positions[0]["symbol"] == "EURUSD"
