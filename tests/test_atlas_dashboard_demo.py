from app import dashboard as dashboard_module


def test_demo_regime_maps_bullish_technical_context():
    regime = dashboard_module._demo_regime_from_technical(
        {
            "price": 100.0,
            "trend": "bullish",
            "momentum": "bullish",
            "volume_state": "high",
            "indicators": {"atr_14": 1.0},
        }
    )

    assert regime["primary_regime"] == "BULL_TREND"
    assert regime["raw_state"]["trend_score"] > 0
    assert regime["raw_state"]["momentum_score"] > 0
    assert regime["raw_state"]["volume_score"] > 0


def test_demo_state_is_resilient_to_symbol_errors(monkeypatch):
    def fake_analyze(symbol, interval, account_balance):
        if symbol == "GAS":
            raise RuntimeError("provider unavailable")
        return {
            "symbol": symbol,
            "interval": interval,
            "status": "NO_TRADE",
            "atlas_decision": {"status": "no_trade"},
        }

    monkeypatch.setattr(
        dashboard_module,
        "_analyze_demo_symbol",
        fake_analyze,
    )
    monkeypatch.setattr(
        dashboard_module,
        "ATLAS_DEMO_SYMBOLS",
        ["XAUUSD", "GAS"],
    )

    state = dashboard_module.atlas_demo_state()

    assert state["status"] == "DEMO_READY"
    assert state["execution"] == "execution-gated"
    assert state["summary"]["analyzed"] == 2
    assert state["summary"]["no_trades"] == 1
    assert state["summary"]["errors"] == 1
    assert state["results"][1]["status"] == "ERROR"
