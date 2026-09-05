from app.intelligence.scoring import Bias, DecisionStatus, Regime
from app.intelligence.scoring.integration import build_scoring_input, score_analysis


def _technical(**overrides):
    base = {
        "price": 100.0,
        "trend": "bullish",
        "momentum": "bullish",
        "macd_signal": "bullish",
        "volume_state": "high",
        "indicators": {"atr_14": 2.0},
        "levels": {"support": 99.0, "resistance": 110.0},
    }
    base.update(overrides)
    return base


def _structure(**overrides):
    base = {
        "structure": "bullish",
        "break_events": [{"type": "BOS_BULLISH"}],
        "liquidity_events": [{"type": "LIQUIDITY_SWEEP_LOW"}],
    }
    base.update(overrides)
    return base


def _regime(**overrides):
    base = {
        "primary_regime": "BULL_TREND",
        "raw_state": {
            "trend_score": 0.8,
            "volatility_score": 0.3,
            "event_risk_score": 0.1,
        },
    }
    base.update(overrides)
    return base


def test_build_scoring_input_maps_existing_engines_without_inventing_macro():
    data = build_scoring_input(
        asset="XAUUSD",
        timeframe="15m",
        technical_analysis=_technical(),
        structure_analysis=_structure(),
        regime_analysis=_regime(),
        risk_reward=2.0,
    )

    assert data.regime is Regime.TRENDING_BULL
    assert data.factors["structure"] == 1.0
    assert data.factors["trend_mtf"] > 0
    assert data.factors["support_resistance"] == 0.5
    assert data.factors["liquidity"] == 0.5
    assert data.factors["momentum"] == 1.0
    assert data.factors["volume"] == 0.5
    assert data.factors["volatility"] == 0.0
    assert data.factors["price_action"] == 1.0
    assert data.factors["macro"] == 0.0


def test_score_analysis_produces_long_candidate_from_aligned_deterministic_inputs():
    result = score_analysis(
        asset="XAUUSD",
        timeframe="15m",
        technical_analysis=_technical(),
        structure_analysis=_structure(),
        regime_analysis=_regime(),
        risk_reward=2.0,
        mtf_trends={"1h": "bullish", "4h": "bullish", "1d": "bullish"},
    )

    assert result.bias is Bias.LONG
    assert result.status is DecisionStatus.VALID
    assert result.long_score >= 60


def test_event_driven_regime_is_hard_veto():
    result = score_analysis(
        asset="EURUSD",
        timeframe="15m",
        technical_analysis=_technical(),
        structure_analysis=_structure(),
        regime_analysis=_regime(
            primary_regime="EVENT_DRIVEN",
            raw_state={
                "trend_score": 0.8,
                "volatility_score": 0.4,
                "event_risk_score": 0.9,
            },
        ),
        risk_reward=2.0,
    )

    assert result.bias is Bias.NEUTRAL
    assert result.status is DecisionStatus.NO_TRADE
    assert "major_event_imminent" in result.veto_reasons


def test_high_volatility_regime_is_hard_veto():
    result = score_analysis(
        asset="XAGUSD",
        timeframe="30m",
        technical_analysis=_technical(),
        structure_analysis=_structure(),
        regime_analysis=_regime(
            primary_regime="HIGH_VOLATILITY",
            raw_state={
                "trend_score": 0.7,
                "volatility_score": 0.9,
                "event_risk_score": 0.1,
            },
        ),
        risk_reward=2.0,
    )

    assert result.status is DecisionStatus.NO_TRADE
    assert "extreme_volatility" in result.veto_reasons


def test_mtf_weighting_respects_higher_timeframes():
    data = build_scoring_input(
        asset="EURUSD",
        timeframe="5m",
        technical_analysis=_technical(trend="bearish"),
        structure_analysis=_structure(),
        regime_analysis=_regime(),
        risk_reward=2.0,
        mtf_trends={
            "5m": "bearish",
            "15m": "bearish",
            "1h": "bullish",
            "4h": "bullish",
            "1d": "bullish",
        },
    )

    assert data.factors["trend_mtf"] > 0


def test_normal_volume_without_directional_confirmation_stays_neutral():
    data = build_scoring_input(
        asset="SOLUSDT",
        timeframe="15m",
        technical_analysis=_technical(
            trend="neutral",
            momentum="overbought",
            macd_signal="neutral",
            volume_state="normal",
        ),
        structure_analysis=_structure(structure="neutral", break_events=[], liquidity_events=[]),
        regime_analysis=_regime(primary_regime="RANGE", raw_state={}),
        risk_reward=2.0,
    )

    assert data.factors["momentum"] == 0.0
    assert data.factors["volume"] == 0.0
    assert data.factors["macro"] == 0.0
