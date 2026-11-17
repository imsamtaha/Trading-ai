import pytest
from tests.test_mt5_submission_safety import terminal, live_terminal, submit
from app.execution.mt5 import MT5ExecutionError
import app.execution.mt5 as adapter


def test_status_command_reports_unresolved_without_resending(live_terminal, monkeypatch, capsys):
    from scripts import mt5_submission_status as cli
    broker, state = live_terminal
    def send(request):
        state.sent.append(request)
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    monkeypatch.setattr(cli, 'MT5Broker', lambda config: broker)
    monkeypatch.setattr(cli, 'load_dotenv', lambda *args: None)
    assert cli.main([]) == 2
    assert '"blocked": true' in capsys.readouterr().out
    assert len(state.sent) == 1


def test_reconcile_command_never_retries_missing_delivery(live_terminal, monkeypatch, capsys):
    from scripts import mt5_submission_status as cli
    broker, state = live_terminal
    def send(request):
        state.sent.append(request)
        return None
    monkeypatch.setattr(adapter.mt5, 'order_send', send)
    with pytest.raises(MT5ExecutionError):
        submit(broker)
    monkeypatch.setattr(cli, 'MT5Broker', lambda config: broker)
    monkeypatch.setattr(cli, 'load_dotenv', lambda *args: None)
    assert cli.main(['--reconcile']) == 2
    assert '"blocked": true' in capsys.readouterr().out
    assert len(state.sent) == 1
