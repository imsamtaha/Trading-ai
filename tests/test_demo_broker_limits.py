import pytest
from types import SimpleNamespace
from tests.test_mt5_submission_safety import terminal, live_terminal, submit
from app.execution.mt5 import MT5ExecutionError


def test_sixth_open_demo_position_is_refused(live_terminal):
    broker, state = live_terminal
    state.positions = [SimpleNamespace(symbol=f'OTHER{i}') for i in range(5)]
    with pytest.raises(MT5ExecutionError, match='open demo'):
        submit(broker)
    assert state.sent == []


def test_sixteenth_demo_entry_is_refused_after_broker_restart(live_terminal):
    broker, state = live_terminal
    for _ in range(15):
        assert submit(broker)['status'] == 'FILLED'
    from app.execution.mt5 import MT5Broker, MT5Config
    restarted = MT5Broker(MT5Config(dry_run=False))
    restarted.connected = True
    restarted.symbol_info = broker.symbol_info
    with pytest.raises(MT5ExecutionError, match='daily demo'):
        submit(restarted)
    assert len(state.sent) == 15


def test_cancelling_before_send_does_not_spend_daily_budget(monkeypatch, tmp_path):
    from app.execution.submission_journal import SubmissionJournal
    monkeypatch.setenv('ATLAS_MT5_SUBMISSION_DB', str(tmp_path/'journal.sqlite'))
    journal=SubmissionJournal()
    account={'login':123,'server':'Test','trade_mode':0}
    for _ in range(16):
        identifier, _ = journal.begin(account, {'symbol':'EURUSD','volume':0.01}, max_daily_entries=15)
        journal.cancel_before_send(identifier)
    identifier, _ = journal.begin(account, {'symbol':'EURUSD','volume':0.01}, max_daily_entries=15)
    journal.finish(identifier,'FILLED')
    assert journal.status(account)['attempts'][0]['state']=='FILLED'


def test_demo_worker_refuses_real_account_before_candles(monkeypatch):
    from scripts import atlas_auto_execution as worker
    class Broker:
        def __init__(self, config): pass
        def connect(self): return {'trade_mode':2}
        def disconnect(self): pass
        def candles(self, *args): pytest.fail('Real account reached demo analysis')
    monkeypatch.setattr(worker,'MT5Broker',Broker)
    monkeypatch.setattr(worker,'AutoExecutionCoordinator',lambda **kwargs: None)
    with pytest.raises(MT5ExecutionError, match='demo account'):
        worker.run_cycle('EURUSD','5m',200,demo_only=True)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ATLAS_DEMO_MAX_DAILY_ENTRIES", "16"),
        ("ATLAS_DEMO_MAX_OPEN_POSITIONS", "6"),
    ],
)
def test_demo_env_limits_cannot_exceed_hard_caps(monkeypatch, live_terminal, name, value):
    broker, state = live_terminal
    monkeypatch.setenv(name, value)
    with pytest.raises(MT5ExecutionError, match="maximums are 15 daily entries and 5 open positions"):
        submit(broker)
    assert state.sent == []
