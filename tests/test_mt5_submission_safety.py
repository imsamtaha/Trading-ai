"""Exercise the real broker boundary; only the external MT5 terminal is simulated."""
from types import SimpleNamespace

import pytest

from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
import app.execution.mt5 as adapter
from tests.test_mt5_risk_snapshot import terminal


def crash_after_reservation(db_path):
    import os
    from app.execution.submission_journal import SubmissionJournal
    os.environ['ATLAS_MT5_SUBMISSION_DB'] = db_path
    SubmissionJournal().begin({'login': 123, 'server': 'Test', 'trade_mode': 0},
                              {'symbol': 'EURUSD', 'volume': 0.02})
    os._exit(7)


def crash_after_broker_delivery(db_path, delivery_path):
    import json
    import os
    import time
    from pathlib import Path
    os.environ['ATLAS_MT5_SUBMISSION_DB'] = db_path
    os.environ['ATLAS_ONE_POSITION_PER_SYMBOL'] = 'true'
    now = time.time()
    def send(request):
        with Path(delivery_path).open('w') as handle:
            json.dump(request, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os._exit(9)
    adapter.mt5 = SimpleNamespace(
        ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1, POSITION_TYPE_BUY=0,
        TRADE_ACTION_DEAL=1, ORDER_TIME_GTC=0, ORDER_FILLING_IOC=1,
        account_info=lambda: SimpleNamespace(login=123, server='Test', trade_mode=0, trade_allowed=True,
                                             equity=10000,margin=0,margin_free=10000),
        order_calc_margin=lambda side,symbol,volume,price:volume*100000*price/200,
        order_calc_profit=lambda side,symbol,volume,entry,stop:((stop-entry) if side==0 else (entry-stop))*100000*volume,
        positions_get=lambda: [], orders_get=lambda: [], order_send=send,
        symbol_info_tick=lambda symbol: SimpleNamespace(bid=1.1, ask=1.1002, time=int(now), time_msc=int(now*1000)))
    broker = MT5Broker(MT5Config(dry_run=False))
    broker.connected = True
    broker.symbol_info = lambda symbol: SimpleNamespace(volume_min=0.01, volume_max=100, volume_step=0.01, digits=5)
    submit(broker)


@pytest.mark.parametrize('phase', ['reserved', 'delivered'])
def test_process_death_leaves_account_blocked(live_terminal, monkeypatch, tmp_path, phase):
    import multiprocessing
    import os
    broker, state = live_terminal
    db_path = os.environ['ATLAS_MT5_SUBMISSION_DB']
    delivery = tmp_path / 'delivery.json'
    target = crash_after_reservation if phase == 'reserved' else crash_after_broker_delivery
    args = (db_path,) if phase == 'reserved' else (db_path, str(delivery))
    process = multiprocessing.get_context('spawn').Process(target=target, args=args)
    process.start()
    process.join(10)
    if process.is_alive():
        process.terminate()
        process.join()
        pytest.fail('Child did not reach simulated crash')
    assert process.exitcode == (7 if phase == 'reserved' else 9)
    if phase == 'delivered':
        assert delivery.is_file()
    with pytest.raises(MT5ExecutionError, match='Unresolved'):
        submit(broker)
    assert state.sent == []


@pytest.fixture
def live_terminal(terminal, monkeypatch, tmp_path):
    broker, state = terminal
    broker.config = MT5Config(dry_run=False)
    monkeypatch.setenv('ATLAS_MT5_SUBMISSION_DB', str(tmp_path / 'submissions.sqlite3'))
    monkeypatch.setenv('ATLAS_ONE_POSITION_PER_SYMBOL', 'true')
    monkeypatch.setattr(adapter.mt5, 'orders_get', lambda **kwargs: [], raising=False)
    monkeypatch.setattr(adapter.mt5, 'TRADE_RETCODE_DONE', 10009, raising=False)
    monkeypatch.setattr(adapter.mt5, 'DEAL_ENTRY_IN', 0, raising=False)
    monkeypatch.setattr(adapter.mt5, 'DEAL_ENTRY_OUT', 1, raising=False)
    monkeypatch.setattr(adapter.mt5, 'ORDER_STATE_FILLED', 4, raising=False)
    monkeypatch.setattr(adapter.mt5, 'shutdown', lambda: None, raising=False)
    state.completed = []
    monkeypatch.setattr(adapter.mt5, 'history_orders_get', lambda **kwargs: state.completed, raising=False)
    monkeypatch.setattr(adapter.mt5, 'history_deals_get', lambda start, end: state.deals)
    def send(request):
        state.sent.append(request)
        return SimpleNamespace(retcode=10009, order=71, deal=72,
                               volume=request['volume'], price=request['price'], comment=request['comment'])
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    return broker, state


def submit(broker):
    return broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12,
                              expected_account={'login': 123, 'server': 'Test', 'trade_mode': 0})


def test_position_appearing_after_snapshot_is_blocked_at_send_boundary(live_terminal):
    broker, state = live_terminal
    assert broker.risk_snapshot()['positions'] == []
    state.positions = [SimpleNamespace(symbol='EURUSD')]
    with pytest.raises(MT5ExecutionError, match='position|Position'):
        submit(broker)
    assert state.sent == []


def test_pending_order_blocks_send(live_terminal, monkeypatch):
    broker, state = live_terminal
    monkeypatch.setattr(adapter.mt5, 'orders_get', lambda **kwargs: [SimpleNamespace(symbol='EURUSD')])
    with pytest.raises(MT5ExecutionError, match='pending|Pending'):
        submit(broker)
    assert state.sent == []


def test_pending_order_on_other_symbol_blocks_automatic_risk_snapshot(live_terminal, monkeypatch):
    broker, state = live_terminal
    monkeypatch.setattr(adapter.mt5, 'orders_get', lambda **kwargs: [SimpleNamespace(symbol='GBPUSD')])
    with pytest.raises(MT5ExecutionError, match='pending|Pending'):
        broker.risk_snapshot()


@pytest.mark.parametrize('reader', ['positions_get', 'orders_get'])
def test_unavailable_final_portfolio_refuses_send(live_terminal, monkeypatch, reader):
    broker, state = live_terminal
    monkeypatch.setattr(adapter.mt5, reader, lambda **kwargs: None)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    assert state.sent == []


@pytest.mark.parametrize('outcome', ['none', 'partial', 'exception'])
def test_uncertain_send_blocks_retry_across_broker_restart(live_terminal, monkeypatch, outcome):
    broker, state = live_terminal
    def send(request):
        state.sent.append(request)
        if outcome == 'exception':
            raise ConnectionError('connection lost after delivery')
        if outcome == 'none':
            return None
        return SimpleNamespace(retcode=10010, order=71, deal=72, volume=0.01,
                               price=1.1002, comment=request['comment'])
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError, match='uncertain|Uncertain'):
        submit(broker)
    # Independent broker instances must see the durable account-wide reservation.
    restarted = MT5Broker(MT5Config(dry_run=False))
    restarted.connected = True
    monkeypatch.setattr(restarted, 'symbol_info', lambda symbol: state.info)
    with pytest.raises(MT5ExecutionError, match='unresolved|Unresolved'):
        restarted.market_order('GBPUSD', 'BUY', 0.02, 1.09, 1.12)
    assert len(state.sent) == 1


def test_unwritable_submission_journal_blocks_before_delivery(live_terminal, monkeypatch, tmp_path):
    broker, state = live_terminal
    monkeypatch.setenv('ATLAS_MT5_SUBMISSION_DB', str(tmp_path))  # directory, not SQLite file
    with pytest.raises(MT5ExecutionError, match='journal|Journal'):
        submit(broker)
    assert state.sent == []


def test_successful_fill_is_recorded_and_can_be_inspected(live_terminal):
    broker, state = live_terminal
    result = submit(broker)
    assert result['status'] == 'FILLED'
    assert result['submission_id']
    report = broker.submission_status()
    assert report['blocked'] is False
    assert report['attempts'][0]['state'] == 'FILLED'
    assert report['attempts'][0]['deal'] == 72
    assert report['attempts'][0]['requested_volume'] == 0.02


def test_reconciliation_does_not_clear_unknown_delivery(live_terminal, monkeypatch):
    broker, state = live_terminal
    monkeypatch.setattr(adapter.mt5, 'order_send', lambda request: None)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    report = broker.reconcile_submissions()
    assert report['blocked'] is True
    with pytest.raises(MT5ExecutionError, match='unresolved|Unresolved'):
        submit(broker)


def test_reconciliation_requires_exact_full_fill_evidence(live_terminal, monkeypatch):
    broker, state = live_terminal
    def delivered_without_ack(request):
        state.sent.append(request)
        state.deals = [SimpleNamespace(type=0, symbol='EURUSD', volume=0.02,
                         order=71, ticket=72, comment=request['comment'], magic=260830,
                         entry=0, profit=0, commission=0, swap=0, fee=0)]
        state.completed = [SimpleNamespace(ticket=71, state=4, symbol='EURUSD', type=0,
                            magic=260830, comment=request['comment'], volume_initial=0.02, volume_current=0)]
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', delivered_without_ack)
    monkeypatch.setattr(adapter.mt5, 'DEAL_ENTRY_IN', 0, raising=False)
    monkeypatch.setattr(adapter.mt5, 'history_deals_get', lambda start, end: state.deals)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    report = broker.reconcile_submissions()
    assert report['blocked'] is False
    assert report['attempts'][0]['state'] == 'FILLED'
    assert report['attempts'][0]['deal'] == 72


@pytest.mark.parametrize('change', [{'volume': 0.01}, {'symbol': 'GBPUSD'},
                                  {'magic': 999}, {'entry': 1}, {'comment': 'unrelated'}])
def test_partial_or_unrelated_history_cannot_release_reservation(live_terminal, monkeypatch, change):
    broker, state = live_terminal
    def send(request):
        deal = dict(type=0, symbol='EURUSD', volume=0.02, order=71, ticket=72,
                    comment=request['comment'], magic=260830, entry=0)
        state.deals = [SimpleNamespace(**{**deal, **change})]
        state.completed = [SimpleNamespace(ticket=71, state=4, symbol='EURUSD', type=0,
                            magic=260830, comment=request['comment'], volume_initial=0.02, volume_current=0)]
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    assert broker.reconcile_submissions()['blocked'] is True


def test_crash_after_delivery_before_ack_record_keeps_reservation(live_terminal, monkeypatch):
    from app.execution.submission_journal import SubmissionJournal, SubmissionJournalError
    broker, state = live_terminal
    finish = SubmissionJournal.finish
    def failed_commit(*args, **kwargs):
        raise SubmissionJournalError('disk failed after fill')
    monkeypatch.setattr(SubmissionJournal, 'finish', failed_commit)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    monkeypatch.setattr(SubmissionJournal, 'finish', finish)
    assert broker.submission_status()['blocked'] is True
    with pytest.raises(MT5ExecutionError, match='Unresolved'):
        submit(broker)
    assert len(state.sent) == 1


def test_failed_uncertain_commit_retains_durable_submitting_state(live_terminal, monkeypatch):
    from app.execution.submission_journal import SubmissionJournal, SubmissionJournalError
    broker, state = live_terminal
    def send(request):
        state.sent.append(request)
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    finish = SubmissionJournal.finish
    monkeypatch.setattr(SubmissionJournal, 'finish',
                        lambda *args, **kwargs: (_ for _ in ()).throw(SubmissionJournalError('disk unavailable')))
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    monkeypatch.setattr(SubmissionJournal, 'finish', finish)
    report = broker.submission_status()
    assert report['blocked'] is True
    assert report['attempts'][0]['state'] == 'SUBMITTING'
    with pytest.raises(MT5ExecutionError, match='Unresolved'):
        submit(broker)
    assert len(state.sent) == 1


def test_coordinator_and_broker_can_share_lock_without_releasing_it(live_terminal):
    from app.execution.portfolio_lock import portfolio_lock
    from concurrent.futures import ThreadPoolExecutor
    broker, state = live_terminal
    with portfolio_lock():
        assert submit(broker)['status'] == 'FILLED'
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(MT5ExecutionError, match='busy'):
                pool.submit(submit, broker).result()
    assert len(state.sent) == 1


def test_direct_market_orders_cannot_overlap_delivery(live_terminal, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    broker, state = live_terminal
    entered, release = Event(), Event()
    send = adapter.mt5.order_send
    def delayed_send(request):
        entered.set()
        assert release.wait(5)
        return send(request)
    monkeypatch.setattr(adapter.mt5, 'order_send', delayed_send)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(submit, broker)
        assert entered.wait(5)
        try:
            with pytest.raises(MT5ExecutionError, match='busy'):
                submit(broker)
        finally:
            release.set()
        assert first.result()['status'] == 'FILLED'
    assert len(state.sent) == 1


def test_changed_other_symbol_exposure_invalidates_approved_snapshot(live_terminal):
    broker, state = live_terminal
    snapshot = broker.risk_snapshot()
    state.positions = [SimpleNamespace(ticket=88, symbol='GBPUSD', type=0, volume=0.1, sl=1.09)]
    with pytest.raises(MT5ExecutionError, match='portfolio|Portfolio'):
        broker.market_order('EURUSD', 'BUY', 0.02, 1.09, 1.12,
                            expected_position_fingerprint=snapshot['position_fingerprint'])
    assert state.sent == []


@pytest.mark.parametrize('change', ['mixed_orders', 'zero_ticket', 'active_remainder', 'history_unavailable'])
def test_reconciliation_requires_one_completed_order(live_terminal, monkeypatch, change):
    broker, state = live_terminal
    def send(request):
        state.deals = [SimpleNamespace(ticket=72, order=71, type=0, entry=0,
                         symbol='EURUSD', volume=0.02, magic=260830, comment=request['comment'])]
        state.completed = [SimpleNamespace(ticket=71, state=4, symbol='EURUSD', type=0,
                            magic=260830, comment=request['comment'], volume_initial=0.02, volume_current=0)]
        if change == 'mixed_orders':
            state.deals[0].volume = 0.01
            state.deals.append(SimpleNamespace(**{**vars(state.deals[0]), 'order': 81, 'ticket': 82}))
        if change == 'zero_ticket':
            state.deals[0].ticket = 0
        if change == 'active_remainder':
            state.completed[0].volume_current = 0.01
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    if change == 'history_unavailable':
        monkeypatch.setattr(adapter.mt5, 'history_orders_get', lambda **kwargs: None)
    try:
        report = broker.reconcile_submissions()
    except MT5ExecutionError:
        report = broker.submission_status()
    assert report['blocked'] is True


def test_uncertain_close_blocks_restart_retry(live_terminal, monkeypatch):
    broker, state = live_terminal
    state.positions = [SimpleNamespace(ticket=88, identifier=87, symbol='EURUSD', type=0, volume=0.02, sl=1.09)]
    monkeypatch.setattr(adapter.mt5, 'symbol_info', lambda symbol: state.info, raising=False)
    def send(request):
        state.sent.append(request)
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        broker.close_position(88)
    restarted = MT5Broker(MT5Config(dry_run=False))
    restarted.connected = True
    with pytest.raises(MT5ExecutionError, match='Unresolved'):
        restarted.close_position(88)
    assert len(state.sent) == 1


def test_account_switch_before_close_cannot_target_new_account(live_terminal, monkeypatch):
    broker, state = live_terminal
    broker._connected_account = {'login': 123, 'server': 'Test', 'trade_mode': 0}
    state.account.login = 999
    state.positions = [SimpleNamespace(ticket=88, identifier=87, symbol='EURUSD', type=0, volume=0.02, sl=1.09)]
    monkeypatch.setattr(adapter.mt5, 'symbol_info', lambda symbol: state.info, raising=False)
    with pytest.raises(MT5ExecutionError, match='account|Account'):
        broker.close_position(88)
    assert state.sent == []


def test_account_switch_between_close_account_reads_refuses_delivery(live_terminal, monkeypatch):
    broker, state = live_terminal
    broker._connected_account = {'login': 123, 'server': 'Test', 'trade_mode': 0}
    expected = SimpleNamespace(**vars(state.account))
    switched = SimpleNamespace(**{**vars(state.account), 'login': 999})
    reads = []
    def account_info():
        reads.append(1)
        return expected if len(reads) == 1 else switched
    monkeypatch.setattr(adapter.mt5, 'account_info', account_info)
    state.positions = [SimpleNamespace(ticket=88, identifier=87, symbol='EURUSD', type=0, volume=0.02, sl=1.09)]
    monkeypatch.setattr(adapter.mt5, 'symbol_info', lambda symbol: state.info, raising=False)
    with pytest.raises(MT5ExecutionError, match='account|Account'):
        broker.close_position(88)
    assert state.sent == []


def test_close_reconciliation_uses_position_identifier_not_ticket(live_terminal, monkeypatch):
    broker, state = live_terminal
    state.positions = [SimpleNamespace(ticket=88, identifier=87, symbol='EURUSD', type=0, volume=0.02, sl=1.09)]
    monkeypatch.setattr(adapter.mt5, 'symbol_info', lambda symbol: state.info, raising=False)
    def send(request):
        state.sent.append(request)
        assert request['position'] == 88
        state.deals = [SimpleNamespace(ticket=72, order=71, type=1, entry=1, position_id=87,
                         symbol='EURUSD', volume=0.02, magic=260830, comment=request['comment'])]
        state.completed = [SimpleNamespace(ticket=71, state=4, symbol='EURUSD', type=1,
                            magic=260830, comment=request['comment'], volume_initial=0.02, volume_current=0)]
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        broker.close_position(88)
    report = broker.reconcile_submissions()
    assert report['blocked'] is False
    assert len(state.sent) == 1
