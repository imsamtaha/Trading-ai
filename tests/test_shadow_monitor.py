import json
from unittest.mock import Mock
from app.monitor.atlas_mt5 import AtlasMT5Monitor

def instance(monkeypatch,tmp_path):
    monkeypatch.setenv("ATLAS_LIVE_TRADING","false")
    monkeypatch.setenv("ATLAS_DEMO_LEDGER",str(tmp_path/"ledger.json"))
    monkeypatch.setenv("ATLAS_SHADOW_TRAINING_ENABLED","true")
    monkeypatch.setenv("ATLAS_SHADOW_REPORT",str(tmp_path/"report.json"))
    monkeypatch.setenv("ATLAS_SHADOW_JOURNAL",str(tmp_path/"predictions.jsonl"))
    monkeypatch.setenv("ATLAS_CATEGORY_POSITION_LIMIT","2")
    monkeypatch.setenv("ATLAS_COUNCIL_TRAINING_ENABLED","false")
    m=AtlasMT5Monitor(symbols=["EURUSD"])
    m.broker=Mock()
    m.heartbeat=Mock()
    m._record_event=Mock(side_effect=lambda event:event)
    return m

def test_preferences_do_not_remove_crypto_or_stocks(monkeypatch,tmp_path):
    m=instance(monkeypatch,tmp_path)
    m.preferred_canonical={"EURUSD"}
    m.broker.symbols.return_value=[
        dict(symbol=s,bid=100,ask=100.01,point=.01,tradeable=True,visible=True)
        for s in ["EURUSD","BITCOIN","ETHEREUM","AAPL.O","TSLA.O"]]
    assert set(m.discover_symbols()) == {"EURUSD","BITCOIN","ETHEREUM","AAPL.O","TSLA.O"}

def test_shadow_abstention_never_changes_paper_action(monkeypatch,tmp_path):
    m=instance(monkeypatch,tmp_path)
    m.auto_discover=False
    m._close_due_positions=Mock(return_value=[])
    candidate=dict(direction="LONG",strategy="LIQUIDITY_RECLAIM",confidence=75,qualified=True)
    m.analyze_symbol=Mock(return_value=dict(candidate=candidate,decision={"decision":"BUY"}))
    m._open_paper_trade=Mock(return_value={"status":"PAPER_TRADE_OPENED"})
    m.shadow_selector.predict=Mock(return_value={"recommendation":"ABSTAIN","changes_trade_decision":False})
    assert m.cycle()[0]["status"]=="PAPER_TRADE_OPENED"
    m._open_paper_trade.assert_called_once()
    lines=(tmp_path/"predictions.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["shadow"]["recommendation"]=="ABSTAIN"
    assert json.loads((tmp_path/"report.json").read_text())["status"]=="INSUFFICIENT_DATA"
    m.broker.order_send.assert_not_called()

def test_crypto_concentration_rejects_before_quote_or_entry(monkeypatch,tmp_path):
    m=instance(monkeypatch,tmp_path)
    m.ledger=Mock()
    m.ledger.last_closed_trade.return_value=None
    m.ledger.has_open_position.return_value=False
    m.ledger.open_positions.return_value=[{"symbol":"BITCOIN"},{"symbol":"ETHEREUM"}]
    event=m._open_paper_trade(timestamp="2026-01-01T00:00:00+00:00",symbol="SOLANA",
        candidate={"direction":"LONG"},decision={"decision":"BUY"})
    assert event["status"]=="NO_TRADE"
    assert "concentration" in event["reason"]
    m.broker.quote.assert_not_called()
    m.ledger.open_trade.assert_not_called()

def test_broker_crypto_names_and_cash_stock_suffixes():
    from app.strategy.universe import normalize_symbol,classify_symbol
    for s in ["BITCOIN","ETHEREUM","SOLANA","XRP","CARDANO","AVALANCHE"]:
        assert classify_symbol(normalize_symbol(s))[0]=="CRYPTO"
    for s in ["AAPL.O","TSLA.O","NVDA.O","V.N","MA.N"]:
        assert classify_symbol(normalize_symbol(s))[0]=="STOCKS"
    assert classify_symbol(normalize_symbol("UNKNOWN")) is None

def test_accelerator_refreshes_once_per_new_settled_count(monkeypatch,tmp_path):
    from app.monitor import atlas_mt5 as module
    monkeypatch.setenv("ATLAS_TRAINING_ACCELERATOR_ENABLED","true")
    m=instance(monkeypatch,tmp_path)
    run=Mock(return_value=Mock(returncode=0,stderr=""))
    monkeypatch.setattr(module.subprocess,"run",run)
    m._refresh_shadow_training()
    m._refresh_shadow_training()
    assert run.call_count == 1
    assert run.call_args.kwargs["timeout"] == 15
    assert "--ledger" in run.call_args.args[0]
    m.broker.order_send.assert_not_called()

def test_scan_order_rotates_without_duplicating_symbols(monkeypatch,tmp_path):
    m=instance(monkeypatch,tmp_path)
    m.auto_discover=False
    m.symbols=["EURUSD","BITCOIN","AAPL.O"]
    m._close_due_positions=Mock(return_value=[])
    order=[]
    m.analyze_symbol=Mock(side_effect=lambda symbol:(order.append(symbol) or {"candidate":None,"decision":{"decision":"WAIT"}}))
    m.cycle()
    assert order==["EURUSD","BITCOIN","AAPL.O"]
    order.clear()
    m.cycle()
    assert order==["BITCOIN","AAPL.O","EURUSD"]
