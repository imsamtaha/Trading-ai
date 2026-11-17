from app.intelligence.scoring.engine import AtlasDecision, Bias, Conviction, DecisionStatus
from app.intelligence.scoring.trade_gate import create_atlas_trade_candidate


def _decision(*, confluence_count=3, conviction=Conviction.MODERATE, risk_reward=2.0):
    factors = ("structure", "trend_mtf", "momentum", "liquidity")[:confluence_count]
    return AtlasDecision(
        asset="EURUSD",
        timeframe="15m",
        regime="trending_bull",
        bias=Bias.LONG,
        conviction=conviction,
        status=DecisionStatus.VALID,
        long_score=70.0,
        short_score=20.0,
        directional_edge=50.0,
        risk_score=20.0,
        risk_reward=risk_reward,
        confluence_count=confluence_count,
        confluence_factors=factors,
        veto_reasons=(),
    )


def _technical():
    return {"price": 1.1000, "indicators": {"atr_14": 0.0010}}


def test_trade_gate_rejects_when_seal_confirmations_are_below_three():
    candidate = create_atlas_trade_candidate(
        decision=_decision(confluence_count=2),
        technical=_technical(),
    )

    assert candidate["status"] == "NO_TRADE"
    assert candidate["executor"]["executor_decision"] == "REJECT_EXECUTION"
    assert "Fewer than 3 independent confirmations." in candidate["executor"]["execution_blockers"]


def test_trade_gate_rejects_low_confidence_before_risk_candidate():
    candidate = create_atlas_trade_candidate(
        decision=_decision(confluence_count=4, conviction=Conviction.LOW),
        technical=_technical(),
    )

    assert candidate["status"] == "NO_TRADE"
    assert candidate["executor"]["executor_decision"] == "REJECT_EXECUTION"
    assert "Signal confidence is below execution threshold." in candidate["executor"]["execution_blockers"]


def test_trade_gate_marks_approved_candidates_as_atlas_seal():
    candidate = create_atlas_trade_candidate(
        decision=_decision(confluence_count=4, conviction=Conviction.HIGH),
        technical=_technical(),
        account_balance=10_000.0,
    )

    assert candidate["status"] == "TRADE_CANDIDATE"
    assert candidate["source"] == "ATLAS_SEAL"
    assert candidate["executor"]["executor_decision"] == "APPROVE_EXECUTION"
    assert candidate["stop_loss_pips"] > 0
    assert candidate["take_profit_pips"] > candidate["stop_loss_pips"]
