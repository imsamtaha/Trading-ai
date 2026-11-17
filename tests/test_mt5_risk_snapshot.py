import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
import app.execution.mt5 as adapter


@pytest.fixture
def terminal(monkeypatch):
    now = time.time()
    state = SimpleNamespace(
        info=SimpleNamespace(volume_min=0.01, volume_max=100.0, volume_step=0.01,
                             trade_tick_size=0.0001, trade_tick_value=10.0, point=0.00001, digits=5),
        account=SimpleNamespace(equity=10000.0, balance=10000.0, login=123, server="Test", trade_mode=0, trade_allowed=True),
        positions=[], deals=[], sent=[],
    )
    def history(start, end):
        assert start.tzinfo is timezone.utc
        assert start.hour == start.minute == start.second == 0
        return state.deals
    api = SimpleNamespace(
        ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1, POSITION_TYPE_BUY=0,
        TRADE_ACTION_DEAL=1, ORDER_TIME_GTC=0, ORDER_FILLING_IOC=1,
        DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        account_info=lambda: state.account, positions_get=lambda **kwargs: state.positions,
        orders_get=lambda **kwargs: [],
        history_deals_get=history,
        symbol_info_tick=lambda symbol: SimpleNamespace(bid=1.1, ask=1.1002, time=int(now), time_msc=int(now*1000)),
        order_calc_profit=lambda side, symbol, volume, entry, stop: ((stop-entry) if side==0 else (entry-stop))*100000*volume,
        last_error=lambda: (1, "unavailable"),
        order_send=lambda request: state.sent.append(request),
    )
    monkeypatch.setattr(adapter, 'mt5', api)
    broker = MT5Broker(MT5Config(dry_run=True))
    broker.connected = True
    monkeypatch.setattr(broker, 'symbol_info', lambda symbol: state.info)
    return broker, state


def test_snapshot_includes_all_symbols_and_realized_costs(terminal):
    broker, state = terminal
    state.deals = [SimpleNamespace(type=0, profit=-290, commission=-5, swap=-3, fee=-2),
                   SimpleNamespace(type=2, profit=9999)]  # deposit excluded
    state.positions = [SimpleNamespace(symbol='EURUSD', type=0, volume=0.1, sl=1.09)]
    result = broker.risk_snapshot()
    assert result['daily_realized_pnl'] == -300
    assert result['open_risk_percent'] == pytest.approx(1.0)
    assert result['equity'] == 10000


@pytest.mark.parametrize('field', ['positions', 'deals'])
def test_snapshot_rejects_missing_terminal_data(terminal, field):
    broker, state = terminal
    setattr(state, field, None)
    with pytest.raises(MT5ExecutionError):
        broker.risk_snapshot()


def test_snapshot_rejects_unprotected_position(terminal):
    broker, state = terminal
    state.positions = [SimpleNamespace(symbol='EURUSD', type=0, volume=0.1, sl=0)]
    with pytest.raises(MT5ExecutionError):
        broker.risk_snapshot()


def test_lot_below_broker_minimum_is_rejected(terminal):
    broker, state = terminal
    with pytest.raises(MT5ExecutionError):
        broker.volume_for_risk('EURUSD', entry=1.1, stop_loss=1.09, risk_amount=1)
    assert state.sent == []


def test_affordable_volume_rounds_down_and_stays_in_budget(terminal):
    broker, state = terminal
    assert broker.volume_for_risk('EURUSD', entry=1.1, stop_loss=1.09, risk_amount=25) == 0.02
    assert state.sent == []


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_sizing_rejects_nonfinite_budget(terminal, value):
    broker, state = terminal
    with pytest.raises(MT5ExecutionError):
        broker.volume_for_risk('EURUSD', entry=1.1, stop_loss=1.09, risk_amount=value)


def test_final_quote_cannot_exceed_approved_cash_risk(terminal):
    broker, state = terminal
    with pytest.raises(MT5ExecutionError):
        broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12, max_cash_risk=20)
    assert state.sent == []


def test_final_quote_cannot_exceed_entry_deviation(terminal):
    broker, state = terminal
    with pytest.raises(MT5ExecutionError):
        broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12,
                            expected_entry=1.09, max_entry_deviation=0.0002)
    assert state.sent == []


@pytest.mark.parametrize('trade_mode,accepted', [(0, True), (2, False)])
def test_active_session_ignores_saved_identity_but_retains_demo_gate(terminal, monkeypatch, trade_mode, accepted):
    broker, state = terminal
    state.account = SimpleNamespace(equity=10000, balance=10000, login=123, server='Active-Demo',
                                    currency='USD', trade_allowed=True, trade_mode=trade_mode)
    monkeypatch.setenv('MT5_REQUIRE_DEMO', 'true')
    monkeypatch.setattr(adapter.mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0, raising=False)
    monkeypatch.setattr(adapter.mt5, 'initialize', lambda *args: True, raising=False)
    monkeypatch.setattr(adapter.mt5, 'shutdown', lambda: None, raising=False)
    broker.config = MT5Config(login=999, server='Saved-Server', password='test', use_active_session=True)
    if accepted:
        assert broker.connect()['login'] == 123
    else:
        with pytest.raises(MT5ExecutionError):
            broker.connect()


def test_final_quote_must_preserve_minimum_reward_risk(terminal, monkeypatch):
    broker, state = terminal
    for name, value in {'TRADE_ACTION_DEAL': 1, 'ORDER_TIME_GTC': 0, 'ORDER_FILLING_IOC': 1}.items():
        monkeypatch.setattr(adapter.mt5, name, value, raising=False)
    with pytest.raises(MT5ExecutionError, match='reward/risk'):
        broker.market_order('EURUSD', 'BUY', 0.01, 1.099, 1.101, max_cash_risk=25)
    assert state.sent == []


def test_final_quote_must_have_fresh_timestamp(terminal, monkeypatch):
    broker, state = terminal
    monkeypatch.setattr(adapter.mt5, 'symbol_info_tick', lambda symbol: SimpleNamespace(
        bid=1.1, ask=1.1002, time=int(time.time()-600), time_msc=0))
    with pytest.raises(MT5ExecutionError, match='stale'):
        broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12, max_cash_risk=25)
    assert state.sent == []


def test_snapshot_rejects_stale_quotes_for_other_open_symbols(terminal, monkeypatch):
    broker, state = terminal
    state.positions = [SimpleNamespace(symbol='GBPUSD', type=0, volume=0.1, sl=1.09)]
    monkeypatch.setattr(adapter.mt5, 'symbol_info_tick', lambda symbol: SimpleNamespace(
        bid=1.1, ask=1.1002, time=int(time.time()-600), time_msc=0))
    with pytest.raises(MT5ExecutionError, match='stale'):
        broker.risk_snapshot()


def test_snapshot_timestamp_reflects_collection_start(terminal, monkeypatch):
    broker, state = terminal
    clock = {'now': 100.0}
    monkeypatch.setattr(adapter.time, 'time', lambda: clock['now'])
    def delayed_account():
        clock['now'] = 700.0
        return state.account
    monkeypatch.setattr(adapter.mt5, 'account_info', delayed_account)
    assert broker.risk_snapshot()['timestamp'] == 100.0


def test_final_valid_request_passes_all_bounds_without_sending_order(terminal):
    broker, state = terminal
    result = broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12, max_cash_risk=25,
                                 expected_entry=1.1000, max_entry_deviation=0.0002)
    assert result['status'] == 'DRY_RUN'
    assert result['volume'] == 0.02
    assert state.sent == []


@pytest.mark.parametrize('equity,balance,deposit', [(12000, 10700, 1000), (12000, 9700, 0), (9000, 9200, -500)])
def test_snapshot_daily_capital_excludes_intraday_flows_and_floating_pnl(terminal, equity, balance, deposit):
    broker, state = terminal
    state.account.equity = equity
    state.account.balance = balance
    state.deals = [SimpleNamespace(type=0, profit=-300), SimpleNamespace(type=2, profit=deposit)]
    result = broker.risk_snapshot()
    assert result['daily_start_capital'] == 10000
    assert result['daily_realized_pnl'] == -300


def test_snapshot_rejects_nonfinite_cash_flow(terminal):
    broker, state = terminal
    state.deals = [SimpleNamespace(type=2, profit=float('nan'))]
    with pytest.raises(MT5ExecutionError):
        broker.risk_snapshot()


def test_snapshot_credit_does_not_change_start_balance(terminal):
    broker, state = terminal
    state.account.balance = 9700
    state.account.equity = 14700
    state.deals = [SimpleNamespace(type=0, profit=-300), SimpleNamespace(type=3, profit=5000)]
    result = broker.risk_snapshot()
    assert result['daily_start_capital'] == 10000
    assert result['daily_realized_pnl'] == -300


@pytest.mark.parametrize('balance', [0, -1, float('nan'), float('inf')])
def test_snapshot_blocks_invalid_start_capital(terminal, balance):
    broker, state = terminal
    state.account.balance = balance
    with pytest.raises(MT5ExecutionError):
        broker.risk_snapshot()


def test_snapshot_blocks_balance_change_during_history_read(terminal, monkeypatch):
    broker, state = terminal
    def close_during_history(start, end):
        state.account = SimpleNamespace(balance=9700, equity=9700, login=123, server="Test", trade_mode=0, trade_allowed=True)
        return [SimpleNamespace(type=0, profit=-300)]
    monkeypatch.setattr(adapter.mt5, 'history_deals_get', close_during_history)
    with pytest.raises(MT5ExecutionError, match='changed'):
        broker.risk_snapshot()


@pytest.mark.parametrize('change', [{'login':999}, {'server':'Different'}, {'trade_mode':2}])
def test_final_submission_rechecks_expected_account(terminal, change):
    broker, state = terminal
    broker.config = MT5Config(dry_run=False)
    state.account = SimpleNamespace(balance=10000, equity=10000, login=123, server='Test', trade_mode=0, trade_allowed=True)
    for key,value in change.items():
        setattr(state.account,key,value)
    with pytest.raises(MT5ExecutionError, match='account|Account'):
        broker.market_order('EURUSD','BUY',0.02,1.09,1.12, max_cash_risk=25,
            expected_account={'login':123,'server':'Test','trade_mode':0})
    assert state.sent == []
