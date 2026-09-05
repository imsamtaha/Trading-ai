import pytest

from app.intelligence.scoring.engine import (
    AtlasScoringEngine,
    Bias,
    Conviction,
    DecisionStatus,
    Regime,
    RiskFlags,
    ScoringInput,
    calculate_position_size,
)


def test_high_conviction_long_requires_score_edge_and_three_factors():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="XAUUSD",
            timeframe="15m",
            regime=Regime.TRENDING_BULL,
            factors={
                "structure": 1.0,
                "trend_mtf": 1.0,
                "support_resistance": 0.8,
                "liquidity": 1.0,
                "momentum": 1.0,
                "volume": 1.0,
                "volatility": 0.0,
                "price_action": 0.0,
                "macro": 0.3,
            },
            risk_score=30,
            risk_reward=2.2,
            account_risk_fraction=0.01,
        )
    )

    assert result.bias is Bias.LONG
    assert result.conviction is Conviction.HIGH
    assert result.status is DecisionStatus.VALID
    assert result.long_score >= 75
    assert result.directional_edge >= 25
    assert result.confluence_count >= 3


def test_single_indicator_cannot_create_directional_trade():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="BTCUSDT",
            timeframe="5m",
            regime=Regime.RANGE_BOUND,
            factors={"momentum": 1.0},
            risk_reward=2.0,
        )
    )
    assert result.bias is Bias.NEUTRAL
    assert result.status is DecisionStatus.NO_TRADE


def test_small_directional_edge_is_neutral():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="EURUSD",
            timeframe="1h",
            regime=Regime.RANGE_BOUND,
            factors={"structure": 0.5, "trend_mtf": -0.5},
            risk_reward=2.0,
        )
    )
    assert result.bias is Bias.NEUTRAL
    assert result.status is DecisionStatus.NO_TRADE


def test_risk_veto_has_priority_over_signal_score():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="SOLUSDT",
            timeframe="15m",
            regime=Regime.TRENDING_BULL,
            factors={
                "structure": 1.0,
                "trend_mtf": 1.0,
                "support_resistance": 1.0,
                "liquidity": 1.0,
                "momentum": 1.0,
            },
            risk_reward=2.5,
            risk_flags=RiskFlags(major_event_imminent=True),
        )
    )
    assert result.long_score == 65
    assert result.bias is Bias.NEUTRAL
    assert result.status is DecisionStatus.NO_TRADE
    assert "major_event_imminent" in result.veto_reasons


def test_low_rr_is_rejected_even_with_strong_signal():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="XRPUSDT",
            timeframe="30m",
            regime=Regime.TRENDING_BULL,
            factors={
                "structure": 1.0,
                "trend_mtf": 1.0,
                "support_resistance": 1.0,
                "liquidity": 0.8,
            },
            risk_reward=1.2,
        )
    )
    assert result.status is DecisionStatus.NO_TRADE
    assert "risk_reward_below_1_5" in result.veto_reasons


def test_missing_volume_does_not_invent_volume_evidence():
    result = AtlasScoringEngine().score(
        ScoringInput(
            asset="ETHUSDT",
            timeframe="1h",
            regime=Regime.TRENDING_BULL,
            factors={"structure": 1.0, "trend_mtf": 1.0},
            risk_reward=2.0,
        )
    )
    assert result.long_score == 35
    assert result.confluence_count == 2


def test_position_size_uses_account_risk_and_stop_distance():
    size = calculate_position_size(
        account_equity=10_000,
        entry_price=100,
        stop_price=95,
        risk_fraction=0.01,
    )
    assert size == pytest.approx(20.0)


def test_position_size_rejects_risk_above_two_percent():
    with pytest.raises(ValueError):
        calculate_position_size(
            account_equity=10_000,
            entry_price=100,
            stop_price=95,
            risk_fraction=0.03,
        )
