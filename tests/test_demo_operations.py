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


def test_demo_status_exposes_performance_center_metrics(status_paths, monkeypatch):
    ledger_path = status_paths.parent / 'ledger.json'
    ledger_path.write_text(json.dumps({
        'open_positions': [],
        'closed_trades': [
            {'symbol':'EURUSD','risk_normalized_pnl':120.0,'r_multiple':1.2,'closed_at':'2026-09-10T10:00:00+00:00'},
            {'symbol':'XAUUSD','risk_normalized_pnl':-50.0,'r_multiple':-0.5,'closed_at':'2026-09-10T11:00:00+00:00'},
            {'symbol':'EURUSD','risk_normalized_pnl':80.0,'r_multiple':0.8,'closed_at':'2026-09-10T12:00:00+00:00'},
        ]
    }))
    write_status('RUNNING', [])

    response = TestClient(app).get('/dashboard/demo-status')
    assert response.status_code == 200
    performance = response.json()['performance']
    assert performance['total_pnl'] == 150.0
    assert performance['win_rate'] == pytest.approx(66.67, abs=0.01)
    assert performance['equity_curve'] == [120.0, 70.0, 150.0]
    assert performance['best_asset']['symbol'] == 'EURUSD'
    assert performance['best_asset']['pnl'] == 200.0
    assert performance['worst_asset']['symbol'] == 'XAUUSD'
    assert performance['worst_asset']['pnl'] == -50.0
    assert len(performance['recent_closed_trades']) == 3


def test_demo_panel_contains_performance_center_ui(status_paths):
    script = TestClient(app).get('/ui/demo-panel.js').text
    assert 'Performance Center' in script
    assert 'demo-win-rate' in script
    assert 'demo-equity-chart' in script
