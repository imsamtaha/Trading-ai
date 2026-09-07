from app.paper_trading.readiness import evaluate_demo_readiness


def _trade(pnl, risk=10.0):
    return {"risk_normalized_pnl": pnl, "risk_amount": risk}


def test_less_than_25_closed_trades_is_not_ready():
    result = evaluate_demo_readiness([_trade(10)] * 24)
    assert result["ready_for_live_review"] is False
    assert result["automatic_live_activation"] is False
    assert result["checks"]["minimum_closed_trades"] is False


def test_25_losing_trades_is_not_ready():
    result = evaluate_demo_readiness([_trade(-10)] * 25)
    assert result["ready_for_live_review"] is False
    assert result["checks"]["positive_expectancy"] is False
    assert result["decision"] == "CONTINUE_FORWARD_DEMO"


def test_profitable_sample_can_only_request_manual_review():
    trades = [_trade(20)] * 17 + [_trade(-10)] * 8
    result = evaluate_demo_readiness(trades)
    assert result["closed_trades"] == 25
    assert result["ready_for_live_review"] is True
    assert result["automatic_live_activation"] is False
    assert result["decision"] == "REVIEW_REQUIRED"
