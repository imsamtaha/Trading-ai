import pytest

from app.intelligence.scoring.engine import (
    AtlasScoringEngine,
    Bias,
    DecisionStatus,
    Regime,
    RiskFlags,
    ScoringInput,
)
from app.intelligence.scoring.trade_gate import (
    atlas_decision_to_signal,
    create_atlas_trade_candidate,
)


def _technical(price=100.0, atr=2.0):
    return {
        "price": price,
        "indicators": {"atr_14": atr},
    }


def _valid_long_decision():
    return AtlasScoringEngine().score(
        ScoringInput(
            asset="XAUUSD",
            timeframe="15m",
            regime=Regime.TRENDING_BULL,
            factors={
                "structure": 1.0,
                "trend_mtf": 1.0,
                "support_resistance": 1.0,
                "liquidity": 1.0,
                "momentum": 1.0,
                "volume": 1.0,
                "macro": 1.0,
            },
            risk_reward=2.0,
        )
    )


def test_atlas_decision_to_signal_preserves_direction_and_scores():
    decision = _valid_long_decision()
    signal = atlas_decision_to_signal(decision)

    assert signal["direction"] == "LONG"
    assert signal["confidence"] == 85
    assert signal["conviction"] == "HIGH"
    assert signal["long_score"] == decision.long_score
    assert signal["atlas_decision"]["status"] == "valid"


def test_valid_atlas_decision_creates_trade_candidate():
    decision = _valid_long_decision()
    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical=_technical(price=100.0, atr=2.0),
        account_balance=10_000.0,
    )

    assert candidate["status"] == "TRADE_CANDIDATE"
    assert candidate["source"] == "ATLAS"
    assert candidate["direction"] == "LONG"
    assert candidate["entry"] == 100.0
    assert candidate["stop_loss"] == pytest.approx(97.0)
    assert candidate["take_profit"] == pytest.approx(106.0)
    assert candidate["risk"]["approved"] is True
    assert candidate["risk"]["risk_reward"] == 2.0


def test_no_trade_decision_is_rejected_by_trade_gate():
    decision = AtlasScoringEngine().score(
        ScoringInput(
            asset="EURUSD",
            timeframe="1h",
            regime=Regime.RANGE_BOUND,
            factors={"momentum": 1.0},
            risk_reward=2.0,
        )
    )

    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical=_technical(),
    )

    assert decision.status is DecisionStatus.NO_TRADE
    assert candidate["status"] == "NO_TRADE"
    assert candidate["reason"] == "ATLAS decision is not valid."


def test_risk_veto_decision_never_becomes_trade_candidate():
    decision = AtlasScoringEngine().score(
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
                "volume": 1.0,
            },
            risk_reward=2.0,
            risk_flags=RiskFlags(major_event_imminent=True),
        )
    )

    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical=_technical(),
    )

    assert decision.bias is Bias.NEUTRAL
    assert candidate["status"] == "NO_TRADE"
    assert "major_event_imminent" in candidate["atlas_decision"]["veto_reasons"]


def test_missing_atr_is_rejected():
    decision = _valid_long_decision()
    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical={"price": 100.0, "indicators": {}},
    )

    assert candidate["status"] == "NO_TRADE"
    assert candidate["reason"] == "Insufficient price or ATR data."


def test_risk_manager_rejects_account_risk_above_two_percent():
    decision = _valid_long_decision()
    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical=_technical(),
        risk_percent=3.0,
    )

    assert candidate["status"] == "NO_TRADE"
    assert candidate["risk"]["approved"] is False
    assert candidate["risk"]["reason"] == "Risk percentage must be between 0 and 2."
