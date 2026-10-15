import pytest
from app.execution.mt5 import MT5ExecutionError
import app.execution.mt5 as adapter
from tests.test_mt5_risk_snapshot import terminal
from tests.test_mt5_submission_safety import live_terminal,submit


def test_snapshot_exposes_native_margin_state(terminal):
    broker,state=terminal
    state.account.margin=4000;state.account.margin_free=6000
    result=broker.risk_snapshot()
    assert result['used_margin']==4000 and result['free_margin']==6000


def test_native_required_margin_is_not_guessed_from_a_leverage_table(terminal,monkeypatch):
    broker,state=terminal
    monkeypatch.setattr(adapter.mt5,'order_calc_margin',lambda *args:123.45,raising=False)
    assert hasattr(broker,'required_margin'),'Native margin calculator missing'
    assert broker.required_margin('EURUSD','BUY',.01,1.1)==123.45


@pytest.mark.parametrize('value',[None,float('nan'),-1,float('inf')])
def test_missing_or_malformed_native_margin_refuses_entry(live_terminal,monkeypatch,value):
    broker,state=live_terminal
    monkeypatch.setattr(adapter.mt5,'order_calc_margin',lambda *args:value,raising=False)
    with pytest.raises(MT5ExecutionError,match='margin|Margin'):
        submit(broker)
    assert state.sent==[]


def test_final_boundary_rechecks_margin_after_portfolio_read(live_terminal,monkeypatch):
    broker,state=live_terminal
    def orders(**kwargs):
        state.account.margin=9900;state.account.margin_free=100
        return []
    monkeypatch.setattr(adapter.mt5,'orders_get',orders)
    with pytest.raises(MT5ExecutionError,match='MARGIN_LEVEL_TOO_LOW'):
        submit(broker)
    assert state.sent==[]
    assert broker.submission_status()['blocked'] is False # definite veto, never delivered


def test_native_free_margin_must_be_observed(live_terminal):
    broker,state=live_terminal
    state.account.margin_free=None
    with pytest.raises(MT5ExecutionError,match='margin|Margin'):
        submit(broker)
    assert state.sent==[]


def test_final_native_gate_reserves_immediate_spread_loss(live_terminal,monkeypatch):
    broker,state=live_terminal
    state.account.equity=1000;state.account.margin=450;state.account.margin_free=550
    monkeypatch.setattr(adapter.mt5,'order_calc_margin',lambda *args:50)
    # The quote has .0002 spread; .02 EURUSD lots incur .40 opening loss.
    with pytest.raises(MT5ExecutionError,match='MARGIN_LEVEL_TOO_LOW'):
        submit(broker)
    assert state.sent==[]


@pytest.mark.parametrize('direction,stop',[('BUY',1.1001),('SELL',1.1001)])
def test_native_entry_rejects_stop_inside_current_spread(live_terminal,direction,stop):
    broker,state=live_terminal
    target=1.12 if direction=='BUY' else 1.08
    with pytest.raises(MT5ExecutionError,match='spread|Spread'):
        broker.market_order('EURUSD',direction,.02,stop,target)
    assert state.sent==[]


def test_final_spread_quote_cannot_be_zero(live_terminal,monkeypatch):
    import time
    from types import SimpleNamespace
    broker,state=live_terminal
    def orders(**kwargs):
        monkeypatch.setattr(adapter.mt5,'symbol_info_tick',lambda symbol:SimpleNamespace(
            bid=0,ask=0,time=int(time.time()),time_msc=int(time.time()*1000)))
        return []
    monkeypatch.setattr(adapter.mt5,'orders_get',orders)
    with pytest.raises(MT5ExecutionError,match='Bid|Ask|quote'):
        submit(broker)
    assert state.sent==[]
    assert broker.submission_status()['blocked'] is False
