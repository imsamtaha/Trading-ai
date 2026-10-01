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


def test_unlimited_daily_entries_keep_loss_protection(tmp_path):
    path = tmp_path / "daily.json"
    broker = GuardedDemoBroker(MT5Config(dry_run=False), login=592031391,
                               server="FxPro-MT5 Demo", state_path=path,
                               max_daily_entries=None)
    for _ in range(50):
        broker._claim_daily_slot(10000.0)
    assert json.loads(path.read_text())["entries"] == 50
    with pytest.raises(MT5ExecutionError, match="Daily demo loss"):
        broker._claim_daily_slot(9700.0)
    assert json.loads(path.read_text())["entries"] == 50


def test_ten_daily_entries_block_the_eleventh(tmp_path):
    path = tmp_path / "daily.json"
    broker = GuardedDemoBroker(MT5Config(dry_run=False), login=592031391,
                               server="FxPro-MT5 Demo", state_path=path,
                               max_daily_entries=10)
    for _ in range(10):
        broker._claim_daily_slot(10000.0)
    with pytest.raises(MT5ExecutionError, match="Daily demo entry limit"):
        broker._claim_daily_slot(10000.0)
    assert json.loads(path.read_text())["entries"] == 10


@pytest.mark.parametrize("count,blocked", [(0,False),(2,False),(3,True),(4,True)])
def test_three_open_position_cap(monkeypatch, count, blocked):
    from app.customer.realtime import guarded_demo
    monkeypatch.setattr(guarded_demo, "mt5", SimpleNamespace(positions_get=lambda: [object()] * count))
    broker = GuardedDemoBroker(MT5Config(), login=592031391, server="FxPro-MT5 Demo", max_open_positions=3)
    if blocked:
        with pytest.raises(MT5ExecutionError, match="Open position limit"):
            broker._open_positions()
    else:
        assert len(broker._open_positions()) == count


def test_positions_unavailable_remains_blocked(monkeypatch):
    from app.customer.realtime import guarded_demo
    monkeypatch.setattr(guarded_demo, "mt5", SimpleNamespace(positions_get=lambda: None))
    broker = GuardedDemoBroker(MT5Config(), login=592031391, server="FxPro-MT5 Demo", max_open_positions=3)
    with pytest.raises(MT5ExecutionError, match="positions unavailable"):
        broker._open_positions()


def test_open_risk_includes_existing_stops(monkeypatch):
    from app.customer.realtime import guarded_demo
    position = SimpleNamespace(type=1,symbol="EURUSD",volume=.01,price_current=1.12,sl=1.125)
    monkeypatch.setattr(guarded_demo, "mt5", SimpleNamespace(positions_get=lambda: [position,position],order_calc_profit=lambda *args: -10))
    broker = GuardedDemoBroker(MT5Config(), login=592031391, server="FxPro-MT5 Demo", max_open_positions=3)
    assert broker.open_risk_pct(10000) == pytest.approx(.2)
    position.sl = 0
    with pytest.raises(MT5ExecutionError, match="protective stop"):
        broker.open_risk_pct(10000)
