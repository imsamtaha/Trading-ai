import json
from types import SimpleNamespace

import pytest

from app.customer.realtime.guarded_demo import GuardedDemoBroker
from app.execution.mt5 import MT5Config, MT5ExecutionError


def test_daily_demo_cap_and_account_identity(tmp_path):
    broker = GuardedDemoBroker(MT5Config(dry_run=False), login=592031391,
                               server="FxPro-MT5 Demo", state_path=tmp_path / "daily.json")
    broker._claim_daily_slot(10000.0)
    saved = json.loads((tmp_path / "daily.json").read_text())
    assert saved["account_id"] == 592031391 and saved["entries"] == 1
    with pytest.raises(MT5ExecutionError, match="Daily demo"):
        broker._claim_daily_slot(10000.0)
    saved["account_id"] = 123
    (tmp_path / "daily.json").write_text(json.dumps(saved))
    with pytest.raises(MT5ExecutionError, match="another account"):
        broker._claim_daily_slot(10000.0)


def test_live_account_fails_before_order(monkeypatch, tmp_path):
    from app.customer.realtime import guarded_demo
    fake = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0)
    monkeypatch.setattr(guarded_demo, "mt5", fake)
    broker = GuardedDemoBroker(MT5Config(dry_run=False), login=592031391,
                               server="FxPro-MT5 Demo", state_path=tmp_path / "daily.json")
    with pytest.raises(MT5ExecutionError, match="Expected FxPro demo"):
        broker._identity(SimpleNamespace(login=592031391, server="FxPro-MT5 Demo", trade_mode=2))


def test_symbol_filling_bitmask_does_not_use_order_enum(monkeypatch):
    from app.execution import mt5 as broker_module
    fake = SimpleNamespace(ORDER_FILLING_FOK=0, ORDER_FILLING_IOC=1,
                           ORDER_FILLING_RETURN=2, SYMBOL_TRADE_EXECUTION_MARKET=2)
    monkeypatch.setattr(broker_module, "mt5", fake)
    broker = GuardedDemoBroker(MT5Config(), login=592031391, server="FxPro-MT5 Demo")
    assert broker._filling_type(SimpleNamespace(filling_mode=2, trade_exemode=2)) == 1
    assert broker._filling_type(SimpleNamespace(filling_mode=1, trade_exemode=2)) == 0
