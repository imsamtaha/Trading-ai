import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.execution.mt5 import MT5Broker, MT5Config, MT5ExecutionError
from app.monitor.atlas_mt5 import AtlasMT5Monitor
from app.monitor.demo_session import write_status


@pytest.fixture
def status_paths(tmp_path, monkeypatch):
    status = tmp_path / 'status.json'
    monkeypatch.setenv('ATLAS_DEMO_STATUS', str(status))
    monkeypatch.setenv('ATLAS_DEMO_LEDGER', str(tmp_path / 'ledger.json'))
    monkeypatch.setenv('ATLAS_SIGNAL_JOURNAL', str(tmp_path / 'journal.jsonl'))
    monkeypatch.setenv('ATLAS_DASHBOARD_ONLY', 'true')
    return status


def test_status_running_stale_and_missing(status_paths):
    client = TestClient(app)
    assert client.get('/dashboard/demo-status').json()['session']['status'] == 'NOT_STARTED'
    write_status('RUNNING', [{'symbol': 'EURUSD', 'status': 'NO_TRADE', 'reason': 'Waiting'}])
    result = client.get('/dashboard/demo-status').json()
    assert result['session']['status'] == 'RUNNING'
    assert result['summary']['closed_trades'] == 0
    assert result['readiness']['ready_for_live_review'] is False
    assert result['automatic_live_activation'] is False
    data = json.loads(status_paths.read_text())
    data['updated_at'] = (datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
    status_paths.write_text(json.dumps(data))
    assert client.get('/dashboard/demo-status').json()['session']['status'] == 'STALE'
    status_paths.write_text('broken')
    assert client.get('/dashboard/demo-status').status_code == 503
    status_paths.write_text('[]')
    assert client.get('/dashboard/demo-status').status_code == 503


def test_status_redacts_provider_error(status_paths):
    write_status('DEGRADED', [{'symbol': 'EURUSD', 'status': 'ERROR', 'reason': 'private-account-details'}])
    assert 'private-account-details' not in status_paths.read_text()


@pytest.mark.parametrize('mode,login,server', [(2,123,'Demo'), (0,999,'Demo'), (0,123,'Other')])
def test_demo_session_rejects_real_or_wrong_account(monkeypatch, mode, login, server):
    monkeypatch.setenv('MT5_REQUIRE_DEMO', 'true')
    fake = SimpleNamespace(initialize=lambda *a: True,
        account_info=lambda: SimpleNamespace(trade_mode=mode,login=login,server=server),
        shutdown=lambda: None, ACCOUNT_TRADE_MODE_DEMO=0)
    monkeypatch.setattr('app.execution.mt5.mt5', fake)
    with pytest.raises(MT5ExecutionError, match='Configured demo account'):
        MT5Broker(MT5Config(login=123, server='Demo')).connect()


def test_monitor_uses_terminal_candles(status_paths, monkeypatch):
    monkeypatch.setenv('ATLAS_LIVE_TRADING', 'false')
    monitor = AtlasMT5Monitor(symbols=['EURUSD'])
    monkeypatch.setattr('app.monitor.atlas_mt5.mt5', SimpleNamespace(TIMEFRAME_M5=5))
    calls = []
    def candles(symbol, timeframe, count):
        calls.append((symbol, timeframe, count))
        return [{'open':1.1,'high':1.11,'low':1.09,'close':1.1,'volume':100} for _ in range(count)]
    monkeypatch.setattr(monitor.broker, 'candles', candles)
    monkeypatch.setattr('app.data.market.get_candles', lambda *a: pytest.fail('Public provider must not be used'))
    result = monitor.analyze_symbol('EURUSD')
    assert calls == [('EURUSD',5,200)]
    assert result['market']['source'] == 'MT5'


def test_monitor_blocks_same_candle_reentry_after_close(status_paths, monkeypatch):
    monkeypatch.setenv('ATLAS_LIVE_TRADING', 'false')
    monitor = AtlasMT5Monitor(symbols=['EURUSD'])
    risk = {
        'approved': True, 'actual_risk_amount': 1.0,
        'risk_percent': 0.75, 'risk_reward': 2.0,
        'position_size': 1000.0,
    }
    monitor.ledger.open_trade(
        symbol='EURUSD', direction='LONG', entry=1.1000,
        stop_loss=1.0990, take_profit=1.1020, position_size=1000.0,
        risk=risk, strategy='CONTINUATION_5M', confidence=85.0,
        timeframe='5m', decision={'decision': 'BUY'},
    )
    monitor.ledger.close_due_positions('EURUSD', bid=1.0990, ask=1.0991)
    candidate = {
        'direction': 'LONG', 'entry': 1.0990, 'stop_loss': 1.0980,
        'take_profit': 1.1010, 'strategy': 'CONTINUATION_5M',
        'confidence': 85.0, 'metadata': {'risk': risk},
    }

    event = monitor._open_paper_trade(
        timestamp=datetime.now(timezone.utc).isoformat(), symbol='EURUSD',
        candidate=candidate, decision={'decision': 'BUY'},
    )

    assert event['status'] == 'SKIPPED'
    assert 'cooldown' in event['reason'].lower()
    assert '(300s remaining)' in event['reason']
    assert monitor.ledger.summary()['open_positions'] == 0


def test_state_alias_and_dashboard_scripts(status_paths, monkeypatch):
    from app.dashboard.api import router
    routes = {r.path:r for r in router.routes if hasattr(r,'path')}
    assert routes['/dashboard/state'].endpoint is routes['/dashboard/atlas'].endpoint
    def unavailable(*args):
        raise MT5ExecutionError('Terminal offline')
    monkeypatch.setattr(MT5Broker, 'connect', unavailable)
    client=TestClient(app)
    assert client.get('/dashboard/state').status_code == 503
    assert '/ui/demo-panel.js' in client.get('/dashboard').text
    assert client.get('/ui/demo-panel.js').status_code == 200
    assert client.post('/mt5/test-order',json={}).status_code == 403
    assert client.post('/agent/paper/execute',json={}).status_code == 403
