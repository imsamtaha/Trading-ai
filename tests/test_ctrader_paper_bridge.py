import csv
import json
import time
from types import SimpleNamespace

import pytest

from app.integrations import ctrader_demo
from app.integrations.ctrader_market import CTraderMarketData
from app.monitor import atlas_mt5
from scripts.run_ctrader_paper import main


ACCOUNT_ID = 4321
SYMBOL_ID = 678


class DemoSocket:
    def __init__(self, *, price=1.1002, stale=False, mismatched=False, scope="SCOPE_VIEW"):
        self.sent = []
        self.incoming = []
        self.price = price
        self.stale = stale
        self.mismatched = mismatched
        self.scope = scope
        self.now_ms = int(time.time() * 1000)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def send(self, raw):
        message = json.loads(raw)
        self.sent.append(message)
        request = message["payloadType"]
        if request == 51:
            return
        scoped = {"ctidTraderAccountId": ACCOUNT_ID}
        payloads = {
            2100: (2101, {}),
            2149: (2150, {"permissionScope": self.scope, "ctidTraderAccount": [
                {"traderLogin": 12345678, "ctidTraderAccountId": ACCOUNT_ID, "isLive": False}
            ]}),
            2102: (2103, scoped),
            2114: (2115, {**scoped, "symbol": [{"symbolName": "EURUSD", "symbolId": SYMBOL_ID, "enabled": True}]}),
            2127: (2128, scoped),
        }
        if request == 2137:
            period = message["payload"]["period"]
            length_minutes = {5: 5, 7: 15}[period]
            boundary = (message["payload"]["toTimestamp"] + 1) // 60000
            bars = [
                {"utcTimestampInMinutes": boundary - step * length_minutes,
                 "low": 109950, "deltaOpen": 10, "deltaHigh": 40, "deltaClose": 30, "volume": 50}
                for step in range(121)
            ]
            reply, payload = 2138, {
                **scoped, "symbolId": SYMBOL_ID, "period": period, "trendbar": bars,
            }
        else:
            reply, payload = payloads[request]
        if request == 2127:
            stamp = self.now_ms - (90_000 if self.stale else 0)
            # A side arriving before the ack must not be discarded.
            spot = {
                "ctidTraderAccountId": ACCOUNT_ID + self.mismatched,
                "symbolId": SYMBOL_ID, "timestamp": stamp,
            }
            self.incoming.append({"payloadType": 2131, "payload": {**spot, "bid": round(self.price * 100000)}})
        self.incoming.append({"payloadType": reply, "clientMsgId": message["clientMsgId"], "payload": payload})
        if request == 2127:
            self.incoming.append({"payloadType": 2131, "payload": {**spot, "ask": round(self.price * 100000) + 10}})

    def recv(self, timeout):
        if not self.incoming:
            raise TimeoutError()
        return json.dumps(self.incoming.pop(0))


@pytest.fixture
def credentials(monkeypatch):
    for key, value in {
        "ATLAS_BROKER_PROVIDER": "ctrader",
        "ATLAS_LIVE_TRADING": "false",
        "ATLAS_CTRADER_CLIENT_ID": "test-client",
        "ATLAS_CTRADER_CLIENT_SECRET": "test-secret",
        "ATLAS_CTRADER_ACCESS_TOKEN": "test-token",
        "ATLAS_CTRADER_DEMO_LOGIN": "12345678",
    }.items():
        monkeypatch.setenv(key, value)


def test_demo_bridge_decodes_closed_bars_and_timestamped_spots(credentials, monkeypatch):
    socket = DemoSocket()
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: socket)
    feed = CTraderMarketData()
    feed.connect()
    try:
        bars = feed.candles("EURUSD", "5m", 120)
        assert len(bars) == 120
        assert bars[-1]["close"] == 1.0998
        assert bars[0]["open_time"] < bars[-1]["open_time"]
        assert bars[-1]["close_time"] <= socket.now_ms
        quote = feed.quote("EURUSD")
        assert quote["bid"] == 1.1002
        assert quote["ask"] == 1.1003
        assert quote["time_msc"] == socket.now_ms
        assert {item["payloadType"] for item in socket.sent} == {2100, 2149, 2102, 2114, 2127, 2137}
    finally:
        feed.disconnect()


@pytest.mark.parametrize(("options", "error"), [
    ({"stale": True}, "PROVIDER_TIMEOUT"),
    ({"mismatched": True}, "ACCOUNT_ID_MISMATCH"),
])
def test_wrong_account_or_stale_quote_cannot_supply_paper_prices(credentials, monkeypatch, options, error):
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: DemoSocket(**options))
    feed = CTraderMarketData()
    feed.connect()
    try:
        with pytest.raises(ctrader_demo.DemoConnectionError, match=error):
            feed.quote("EURUSD")
    finally:
        feed.disconnect()


def test_trade_scope_is_rejected_before_any_market_request(credentials, monkeypatch):
    socket = DemoSocket(scope="SCOPE_TRADE")
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: socket)
    with pytest.raises(ctrader_demo.DemoConnectionError, match="VIEW_ONLY_AUTHORIZATION_REQUIRED"):
        CTraderMarketData().connect()
    assert [item["payloadType"] for item in socket.sent] == [2100, 2149]


def test_candle_export_matches_research_input_and_does_not_overwrite(credentials, monkeypatch, tmp_path):
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: DemoSocket())
    output = tmp_path / "EURUSD_M15.csv"
    args = ["--symbols", "EURUSD", "--interval", "15m", "--export-candles", str(output)]
    assert main(args) == 0
    original = output.read_bytes()
    with output.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["time", "open", "high", "low", "close"]
        rows = list(reader)
    assert len(rows) == 120
    assert rows[0]["time"] < rows[-1]["time"]
    assert main(args) == 1
    assert output.read_bytes() == original


def test_monitor_runs_paper_entry_and_settlement_through_ctrader(credentials, monkeypatch, tmp_path):
    starts = iter([DemoSocket(), DemoSocket(price=1.103)])
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: next(starts))

    def fail_mt5(_):
        pytest.fail("The cTrader worker constructed an MT5 broker")

    monkeypatch.setattr(atlas_mt5, "MT5Broker", fail_mt5)
    monkeypatch.delenv("ATLAS_SHADOW_TRAINING_ENABLED", raising=False)
    monkeypatch.setenv("ATLAS_DEMO_LEDGER", str(tmp_path / "mt5_ledger.json"))
    candidate = {
        "direction": "LONG", "entry": 1.1000, "stop_loss": 1.0990,
        "take_profit": 1.1020, "strategy": "CONTINUATION_5M", "confidence": 85.0,
        "qualified": True, "regime": "BULL_TREND", "metadata": {"risk": {"risk_percent": 0.5}},
    }
    monkeypatch.setattr(atlas_mt5, "generate_strategy_candidate", lambda *a, **kw:
                        SimpleNamespace(to_dict=lambda: candidate))
    monkeypatch.setattr(atlas_mt5.AtlasMT5Monitor, "_decision_from_candidate", lambda *_: {
        "decision": "BUY", "score": 88.0, "confidence": 82.0, "risk_level": "LOW",
        "conflict_score": 0.0, "event_risk_score": 0.0, "volatility_score": 0.0,
    })
    state = tmp_path / "ctrader"
    args = ["--once", "--symbols", "EURUSD", "--state-dir", str(state)]
    assert main(args) == 0
    assert main(args) == 0

    journal = [json.loads(line) for line in (state / "signals.jsonl").read_text().splitlines()]
    opened = next(event for event in journal if event["status"] == "PAPER_TRADE_OPENED")
    closed = next(event for event in journal if event["status"] == "PAPER_TRADE_CLOSED")
    assert opened["market_source"] == closed["market_source"] == "CTRADER_DEMO"
    assert opened["trade_intent"]["execution_environment"] == "PAPER"
    assert opened["trade_intent"]["broker_execution_allowed"] is False
    assert closed["training"]["total_examples"] == 1
    assert (state / "council_profile.json").is_file()
    assert (state / "shadow_report.json").is_file()
    assert not (tmp_path / "mt5_ledger.json").exists()
