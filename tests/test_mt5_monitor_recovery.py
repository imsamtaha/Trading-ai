from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.monitor import atlas_mt5 as module
from app.execution.mt5 import MT5ExecutionError


def monitor(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "ledger.json"))
    instance = module.AtlasMT5Monitor(symbols=["EURUSD"])
    instance.broker = Mock()
    instance.heartbeat = Mock()
    instance._record_event = Mock(side_effect=lambda event: event)
    return instance


def test_reconnect_after_initial_failure(monkeypatch, tmp_path):
    instance = monitor(monkeypatch, tmp_path)
    instance.broker.connect.side_effect = [MT5ExecutionError("offline"), {"equity": 10000}]
    instance.discover_symbols = Mock()
    def cycle():
        instance.stop()
        return []
    instance.cycle = Mock(side_effect=cycle)
    monkeypatch.setattr(module.time, "sleep", Mock())
    instance.run_forever()
    assert instance.broker.connect.call_count == 2
    instance.cycle.assert_called_once()
    instance.heartbeat.publish_connection.assert_any_call({}, "error")
    instance.broker.order_send.assert_not_called()
    assert instance.running is False


def test_discovery_failure_disconnects(monkeypatch, tmp_path):
    instance = monitor(monkeypatch, tmp_path)
    instance.broker.connect.return_value = {"equity": 10000}
    instance.discover_symbols = Mock(side_effect=MT5ExecutionError("symbols unavailable"))
    with pytest.raises(MT5ExecutionError):
        instance.run_once()
    instance.broker.disconnect.assert_called_once()


def test_analysis_uses_broker_exact_candles(monkeypatch, tmp_path):
    instance = monitor(monkeypatch, tmp_path)
    candles = [{"close": 1.1}] * 50
    instance.broker.candles.return_value = candles
    monkeypatch.setattr(module, "mt5", SimpleNamespace(TIMEFRAME_M5=5))
    technical = Mock(return_value={})
    monkeypatch.setattr(module, "analyze_candles", technical)
    monkeypatch.setattr(module, "analyze_structure", Mock(return_value={}))
    monkeypatch.setattr(module, "generate_strategy_candidate", Mock(return_value=None))
    result = instance.analyze_symbol("EURUSD.fx")
    instance.broker.candles.assert_called_once_with("EURUSD.fx", 5, 200)
    technical.assert_called_once_with(candles)
    assert result["market"]["source"] == "MT5"


def test_missing_ledger_is_unknown(monkeypatch, tmp_path, capsys):
    from scripts.atlas_demo_status import main
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "missing.json"))
    assert main() == 2
    assert '"summary": null' in capsys.readouterr().out
