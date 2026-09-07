from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.agent.core import AtlasAgent
from app.agent.models import AgentRequest, MULTI_TIMEFRAMES
from app.main import app
from app.strategies.signal import generate_signal
from app.strategies.trade import create_trade_candidate


@pytest.fixture
def analyses(monkeypatch):
    frames = {}
    for index, interval in enumerate(MULTI_TIMEFRAMES):
        technical = {"trend": "bullish", "momentum": "bullish", "macd_signal": "bullish",
                     "price": 100 + index, "indicators": {"atr_14": 2}}
        structure = {"structure": "bullish"}
        signal = generate_signal(technical, structure)
        frames[interval] = {"symbol": "EURUSD", "interval": interval,
                            "technical": technical, "structure": structure, "signal": signal,
                            "trade": create_trade_candidate(signal, technical)}

    def analyze(**kwargs):
        assert kwargs["symbol"] == "EURUSD"
        assert kwargs["limit"] == 120
        assert kwargs["account_balance"] == 20000
        frame = frames[kwargs["interval"]]
        if isinstance(frame, Exception):
            raise frame
        return deepcopy(frame)

    monkeypatch.setattr("app.agent.core.market_analysis", analyze)
    # Any execution call is a regression, even when paper execution is enabled.
    def forbidden(*args, **kwargs):
        pytest.fail("Decision assessment must never execute an order")
    monkeypatch.setattr("app.agent.tools.paper_execute", forbidden)
    monkeypatch.setattr("app.agent.tools.PersistentPaperTradingEngine", forbidden)
    monkeypatch.setenv("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "true")
    return frames


def assess():
    return AtlasAgent().assess_multi_timeframe(
        AgentRequest("EURUSD", limit=120, account_balance=20000, risk_percent=0.5))


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_unanimous_engines_preserve_5m_levels_and_risk(analyses, direction):
    if direction == "SHORT":
        for frame in analyses.values():
            frame["technical"].update(trend="bearish", momentum="bearish", macd_signal="bearish")
            frame["structure"]["structure"] = "bearish"
            frame["signal"] = generate_signal(frame["technical"], frame["structure"])
            frame["trade"] = create_trade_candidate(frame["signal"], frame["technical"])
    analyses["30m"]["signal"]["confidence"] = 77
    original = deepcopy(analyses)
    result = assess()
    assert result.decision == "PAPER_CANDIDATE"
    assert result.paper_only is True
    assert result.confidence == 77
    assert result.candidate_interval == "5m"
    assert list(result.timeframe_decisions) == list(MULTI_TIMEFRAMES)
    assert result.signal["direction"] == direction
    for key in ("entry", "stop_loss", "take_profit", "direction"):
        assert result.trade[key] == analyses["5m"]["trade"][key]
    assert result.risk["approved"] is True
    assert result.trade["risk"] == result.risk
    assert analyses == original
    for frame in result.timeframe_decisions.values():
        assert frame["risk"]["maximum_risk_amount"] == 100  # 0.5% of requested balance


@pytest.mark.parametrize("interval", MULTI_TIMEFRAMES)
@pytest.mark.parametrize("failure", ["conflict", "neutral", "risk", "unavailable", "malformed", "identity", "nan"])
def test_any_frame_can_veto(analyses, interval, failure):
    frame = analyses[interval]
    if failure == "conflict":
        frame["signal"]["direction"] = "SHORT"
        frame["trade"].update(direction="SHORT", stop_loss=110, take_profit=80)
    elif failure == "neutral":
        frame["signal"]["direction"] = "WAIT"
        frame["trade"] = {"status": "NO_TRADE"}
    elif failure == "risk":
        frame["trade"]["take_profit"] = frame["trade"]["entry"]
    elif failure == "unavailable":
        analyses[interval] = TimeoutError("provider private details")
    elif failure == "malformed":
        del frame["technical"]
    elif failure == "identity":
        frame["interval"] = "4h"
    else:
        frame["signal"]["confidence"] = float("nan")
    result = assess()
    assert result.decision == "WAIT"
    assert result.confidence == 0
    assert result.risk["approved"] is False
    assert result.trade["status"] == "NO_TRADE"
    assert "entry" not in result.trade
    assert result.candidate_interval is None
    assert len(result.timeframe_decisions) == 4
    assert any(interval in reason for reason in result.rationale) or failure == "conflict"
    assert "provider private details" not in str(result.to_dict())


def test_api_multi_and_single_mode_and_execution_guard(analyses, monkeypatch):
    monkeypatch.setenv("ATLAS_DASHBOARD_ONLY", "true")
    monkeypatch.setenv("ATLAS_LIVE_TRADING", "false")
    client = TestClient(app)
    payload = {"symbol": "eurusd", "limit": 120, "account_balance": 20000, "risk_percent": 0.5}
    single = client.post("/agent/decision", json=payload)
    assert single.status_code == 200
    assert single.json()["interval"] == "1h"
    assert single.json()["timeframe_decisions"] == {}
    multi = client.post("/agent/decision", json=dict(payload, multi_timeframe=True))
    assert multi.status_code == 200
    assert multi.json()["interval"] == "multi"
    assert len(multi.json()["timeframe_decisions"]) == 4
    assert multi.json()["paper_only"] is True
    assert client.post("/agent/paper/execute", json={}).status_code == 403
    assert client.post("/mt5/test-order", json={}).status_code == 403
    assert client.get("/agent/capabilities").json()["multi_timeframes"] == list(MULTI_TIMEFRAMES)
    analyses["15m"] = TimeoutError()
    assert client.post("/agent/decision", json=dict(payload, multi_timeframe=True)).json()["decision"] == "WAIT"


@pytest.mark.parametrize("field,value", [("limit", 49), ("risk_percent", 3), ("account_balance", 0)])
def test_api_validates_multi_inputs(field, value):
    response = TestClient(app).post("/agent/decision", json={"symbol": "EURUSD", "multi_timeframe": True, field: value})
    assert response.status_code == 422
