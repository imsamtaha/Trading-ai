from app.hub.pipeline import build_mtf_consensus, evaluate_scan


def _scan(trends):
    return {
        "symbol": "XAUUSD",
        "timeframes": {
            tf: {"technical": {"trend": trend}}
            for tf, trend in trends.items()
        },
        "errors": {},
    }


def test_full_bullish_alignment_approves_buy():
    result = build_mtf_consensus(_scan({"5m": "BULLISH", "15m": "BULLISH", "30m": "BULLISH", "1h": "BULLISH"}))
    assert result.action == "BUY"
    assert result.approved is True
    assert result.confidence == 100.0


def test_conflicting_timeframes_wait():
    result = build_mtf_consensus(_scan({"5m": "BULLISH", "15m": "BEARISH", "30m": "BULLISH", "1h": "BULLISH"}))
    assert result.action == "WAIT"
    assert result.approved is False


def test_missing_data_waits():
    result = evaluate_scan({"symbol": "XAUUSD", "timeframes": {}, "errors": {"5m": "timeout"}})
    assert result["action"] == "WAIT"
    assert result["approved"] is False
