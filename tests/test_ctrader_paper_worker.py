import json
import time
from collections import deque
from types import SimpleNamespace

import pytest

from app.integrations import ctrader_demo
from app.monitor import atlas_mt5
from app.monitor.atlas_ctrader import AtlasCTraderPaperMonitor
from app.owner_dashboard import read_evidence


class DemoMarketSocket:
    def __init__(self, bid: int, timestamp: int, account_id: int = 321):
        self.bid = bid
        self.timestamp = timestamp
        self.account_id = account_id
        self.requests = []
        self.messages = deque()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def send(self, wire):
        request = json.loads(wire)
        kind = request["payloadType"]
        self.requests.append(kind)
        account = {"ctidTraderAccountId": self.account_id}
        if kind == 2100:
            reply = {}
        elif kind == 2149:
            reply = {"permissionScope": 0, "ctidTraderAccount": [
                {**account, "traderLogin": 12345678, "isLive": False},
            ]}
        elif kind == 2102:
            reply = account
        elif kind == 2114:
            reply = {**account, "symbol": [{"symbolId": "44", "symbolName": "EURUSD", "enabled": True}]}
        elif kind == 2127:
            assert request["payload"]["subscribeToSpotTimestamp"] is True
            assert request["payload"]["symbolId"] == [44]
            for side, price in (("bid", self.bid), ("ask", self.bid + 10)):
                self.messages.append({"payloadType": 2131, "payload": {
                    **account, "symbolId": 44, "timestamp": self.timestamp, side: str(price),
                }})
            reply = account
        elif kind == 2137:
            latest = int(time.time()) // 300 * 5 - 5
            reply = {**account, "period": 5, "symbolId": 44, "trendbar": [
                {"utcTimestampInMinutes": latest - 5 * i, "volume": 100,
                 "low": 109990, "deltaOpen": 1, "deltaHigh": 20, "deltaClose": 10}
                for i in range(100)
            ]}
        else:
            raise AssertionError(f"Unexpected cTrader request {kind}")
        self.messages.append({"payloadType": kind + 1, "clientMsgId": request["clientMsgId"], "payload": reply})

    def recv(self, timeout):
        if not self.messages:
            raise TimeoutError
        return json.dumps(self.messages.popleft())


@pytest.fixture
def demo_env(monkeypatch):
    for name, value in {
        "ATLAS_BROKER_PROVIDER": "ctrader",
        "ATLAS_LIVE_TRADING": "false",
        "ATLAS_CTRADER_DEMO_LOGIN": "12345678",
        "ATLAS_CTRADER_CLIENT_ID": "fixture-client",
        "ATLAS_CTRADER_CLIENT_SECRET": "fixture-secret",
        "ATLAS_CTRADER_ACCESS_TOKEN": "fixture-token",
        "ATLAS_OWNER_SNAPSHOT_HMAC_KEY": "fixture-key-" * 4,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ATLAS_COUNCIL_TRAINING_ENABLED", raising=False)


def test_worker_settles_and_signs_only_after_a_fresh_demo_quote(demo_env, monkeypatch, tmp_path):
    def strategy(symbol, technical, structure, **kwargs):
        return SimpleNamespace(to_dict=lambda: {
            "direction": "LONG", "entry": 1.1000, "stop_loss": 1.0990, "take_profit": 1.1020,
            "strategy": "CONTINUATION_5M", "confidence": 85.0, "qualified": True, "regime": "BULL_TREND",
            "metadata": {"risk": {"risk_percent": 0.5}},
        })

    monkeypatch.setattr(atlas_mt5, "generate_strategy_candidate", strategy)
    worker = AtlasCTraderPaperMonitor(state_dir=tmp_path, symbols=["EURUSD"])
    monkeypatch.setattr(worker, "_decision_from_candidate", lambda candidate: {
        "decision": "BUY", "score": 88.0, "confidence": 82.0, "risk_level": "LOW",
    })
    now = int(time.time() * 1000)
    opened_session = DemoMarketSocket(110000, now)
    stale_session = DemoMarketSocket(110300, now - 60_000)
    old_entry_session = DemoMarketSocket(110300, now - 200)
    settled_session = DemoMarketSocket(110300, now + 1500)
    sessions = iter([opened_session, stale_session, old_entry_session, settled_session])
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: next(sessions))
    monkeypatch.setenv("ATLAS_OWNER_SNAPSHOT_PATH", str(tmp_path / "atlas_owner_snapshot.json"))

    assert worker.run_once()[0]["status"] == "PAPER_TRADE_OPENED"
    assert worker.ledger.closed_trades() == []
    assert read_evidence()["data"]["training_progress"]["sample_count"] == 0
    assert worker.run_once()[0]["reason"] == "NO_FRESH_CTRADER_QUOTE"
    assert worker.run_once()[0]["reason"] == "CTRADER_QUOTE_PRECEDES_PAPER_ENTRY"
    assert worker.ledger.closed_trades() == []
    assert worker.run_once()[0]["status"] == "PAPER_TRADE_CLOSED"
    assert len(worker.ledger.closed_trades()) == 1
    assert len(worker.council_training_journal.load()) == 1
    evidence = read_evidence()
    assert evidence["verified"] is True
    assert evidence["data_origin"] == "CTRADER_DEMO_PAPER"
    assert evidence["data"]["paper_trade_history"][0]["source"] == "ctrader_demo_paper_ledger"
    assert evidence["data"]["training_progress"]["sample_count"] == 1
    assert "fixture-token" not in json.dumps(evidence)
    assert opened_session.requests == [2100, 2149, 2102, 2114, 2127, 2137]


def test_worker_does_not_reuse_other_account_or_mt5_ledger(demo_env, monkeypatch, tmp_path):
    worker = AtlasCTraderPaperMonitor(state_dir=tmp_path, symbols=["EURUSD"])
    worker.ledger.path.write_text('{"open_positions": [], "closed_trades": []}')
    session = DemoMarketSocket(110000, int(time.time() * 1000))
    monkeypatch.setattr(ctrader_demo, "connect", lambda *args, **kwargs: session)
    with pytest.raises(ctrader_demo.DemoConnectionError, match="NO_ACCOUNT_BINDING"):
        worker.run_once()
    assert session.requests == [2100, 2149, 2102]
    assert not (tmp_path / "atlas_owner_snapshot.json").exists()

    worker.ledger.path.unlink()
    worker._bind_state_to_account(555)
    with pytest.raises(ctrader_demo.DemoConnectionError, match="ANOTHER_ACCOUNT"):
        worker.run_once()
