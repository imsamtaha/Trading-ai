from inspect import signature

from app.dashboard.api import _monitor_symbol


def test_monitor_symbol_accepts_risk_state():
    params = signature(_monitor_symbol).parameters

    assert "risk_state" in params

def test_monitor_symbol_returns_fail_closed_risk_when_state_missing():
    import inspect

    from app.dashboard.api import _monitor_symbol

    params = inspect.signature(_monitor_symbol).parameters
    assert "risk_state" in params

def test_monitor_symbol_returns_fail_closed_risk_when_state_missing(monkeypatch):
    import app.dashboard.api as dashboard_api

    class FakeBroker:
        def quote(self, symbol):
            return {
                "last": 100.0,
                "bid": 99.9,
                "ask": 100.1,
                "spread_points": 2.0,
            }

    class FakeQualityEngine:
        def evaluate(self, decision, mtf_alignment):
            return {"signal_quality": "TEST"}

    def fake_analyze_timeframe(broker, symbol, mt5_tf, count):
        return {
            "technical": {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "macd_signal": "NEUTRAL",
            },
            "structure": {
                "structure": "RANGE",
            },
            "signal": {
                "direction": "WAIT",
                "score": 0.0,
            },
        }

    def fake_build_decision(results):
        return (
            {
                "decision": "WAIT",
                "mtf_alignment": "UNKNOWN",
            },
            None,
            None,
            None,
        )

    monkeypatch.setattr(
        dashboard_api,
        "SignalQualityEngine",
        FakeQualityEngine,
    )

    monkeypatch.setattr(
        dashboard_api,
        "_analysis_tools",
        lambda: (
            {"5m": "TEST_TF"},
            fake_analyze_timeframe,
            fake_build_decision,
        ),
    )

    result = dashboard_api._monitor_symbol(
        FakeBroker(),
        "GOLD",
        "XAUUSD",
        "METAL",
        0.0,
        risk_state=None,
    )

    assert result["risk"]["action"] == "BLOCK"
    assert result["risk"]["risk_level"] == "HARD_BLOCK"
    assert result["risk"]["reasons"] == ["MISSING_RISK_DATA"]

def test_monitor_symbol_evaluates_raw_risk_state_with_real_engine(monkeypatch):
    import app.dashboard.api as dashboard_api

    class FakeBroker:
        def quote(self, symbol):
            return {
                "last": 100.0,
                "bid": 99.9,
                "ask": 100.1,
                "spread_points": 2.0,
            }

    class FakeQualityEngine:
        def evaluate(self, decision, mtf_alignment):
            return {"signal_quality": "TEST"}

    def fake_analyze_timeframe(broker, symbol, mt5_tf, count):
        return {
            "technical": {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "macd_signal": "NEUTRAL",
            },
            "structure": {
                "structure": "RANGE",
            },
            "signal": {
                "direction": "WAIT",
                "score": 0.0,
            },
        }

    def fake_build_decision(results):
        return (
            {
                "decision": "WAIT",
                "mtf_alignment": "UNKNOWN",
            },
            None,
            None,
            None,
        )

    monkeypatch.setattr(
        dashboard_api,
        "SignalQualityEngine",
        FakeQualityEngine,
    )

    monkeypatch.setattr(
        dashboard_api,
        "_analysis_tools",
        lambda: (
            {"5m": "TEST_TF"},
            fake_analyze_timeframe,
            fake_build_decision,
        ),
    )

    raw_risk_state = {
        "risk_percent": 0.50,
        "daily_loss_percent": 0.0,
        "weekly_loss_percent": 0.0,
        "drawdown_percent": 0.0,
        "open_positions": 0,
        "same_symbol_positions": 0,
        "spread_ok": True,
        "data_fresh": True,
        "stop_loss_valid": True,
    }

    result = dashboard_api._monitor_symbol(
        FakeBroker(),
        "GOLD",
        "XAUUSD",
        "METAL",
        0.0,
        risk_state=raw_risk_state,
    )

    assert result["risk"]["action"] == "ALLOW_DEMO"
    assert result["risk"]["risk_level"] == "ELIGIBLE"
    assert result["risk"]["policy_version"] == "atlas-risk-v1"

def test_build_position_risk_state_counts_positions():
    from app.dashboard.api import _build_position_risk_state

    positions = [
        {"symbol": "GOLD"},
        {"symbol": "EURUSD"},
    ]

    state = _build_position_risk_state(
        positions=positions,
        symbol="GOLD",
    )

    assert state["open_positions"] == 2
    assert state["same_symbol_positions"] == 1
    assert state["daily_loss_percent"] is None
    assert state["weekly_loss_percent"] is None
    assert state["drawdown_percent"] is None

def test_dashboard_risk_state_counts_open_positions():
    from app.dashboard.api import _build_position_risk_state

    positions = [
        {"symbol": "GOLD"},
        {"symbol": "EURUSD"},
        {"symbol": "GOLD"},
    ]

    state = _build_position_risk_state(
        positions=positions,
        symbol="GOLD",
    )

    assert state["open_positions"] == 3
    assert state["same_symbol_positions"] == 2

