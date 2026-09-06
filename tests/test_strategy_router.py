from app.strategies.router import generate_strategy_candidate


def _technical(direction: str) -> dict:
    bullish = direction == "LONG"
    bias = "bullish" if bullish else "bearish"
    return {
        "price": 100.0,
        "trend": bias,
        "momentum": bias,
        "macd_signal": bias,
        "indicators": {"atr_14": 2.0, "rsi_14": 55.0 if bullish else 45.0},
    }


def test_balanced_bullish_trend_qualifies_prime_candidate():
    candidate = generate_strategy_candidate(
        "XAUUSD",
        _technical("LONG"),
        {"structure": "bullish"},
        mode="BALANCED",
    )
    assert candidate is not None
    assert candidate.direction == "LONG"
    assert candidate.strategy == "CONTINUATION_5M"
    assert candidate.qualified is True
    assert candidate.classification in {"A", "A+"}
    assert candidate.risk_reward >= 1.5


def test_balanced_bearish_trend_qualifies_prime_candidate():
    candidate = generate_strategy_candidate(
        "EURUSD",
        _technical("SHORT"),
        {"structure": "bearish"},
        mode="BALANCED",
    )
    assert candidate is not None
    assert candidate.direction == "SHORT"
    assert candidate.qualified is True


def test_ambiguous_market_returns_no_candidate():
    candidate = generate_strategy_candidate(
        "XAUUSD",
        {
            "price": 100.0,
            "trend": "neutral",
            "momentum": "neutral",
            "macd_signal": "neutral",
            "indicators": {"atr_14": 2.0, "rsi_14": 50.0},
        },
        {"structure": "neutral"},
        mode="ACTIVE",
    )
    assert candidate is None
