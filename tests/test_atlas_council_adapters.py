import pytest

from app.intelligence.council_adapters import (
    build_paper_council,
    record_settled_paper_outcome,
)
from app.intelligence.council_training import CouncilTrainingJournal


def _signal(direction="LONG", confidence=80):
    return {
        "direction": direction,
        "confidence": confidence,
        "reasons": ["trend aligned", "momentum aligned"],
    }


def _risk(approved=True):
    return {
        "approved": approved,
        "reason": "Risk parameters acceptable." if approved else "Risk limit reached.",
    }


def test_existing_components_build_a_paper_only_council_intent():
    result = build_paper_council(
        symbol="EURUSD",
        snapshot_id="snap-1",
        signal=_signal(),
        risk=_risk(),
        data_quality=0.95,
        event_state={
            "market_bias": "NEUTRAL",
            "risk_level": "LOW",
            "confidence": 0.4,
        },
        quality={
            "execution_confidence": 70,
            "signal_quality": "MEDIUM",
            "evidence_quality": 80,
        },
    )

    council = result["council"]
    intent = result["trade_intent"]
    assert [item["agent"] for item in council["opinions"]] == [
        "technical",
        "event_intelligence",
        "confidence",
    ]
    assert intent["decision"] == "BUY"
    assert intent["execution_environment"] == "PAPER"
    assert intent["broker_execution_allowed"] is False


def test_senior_risk_rejection_forces_hold_through_adapter():
    result = build_paper_council(
        symbol="EURUSD",
        snapshot_id="snap-1",
        signal=_signal(),
        risk=_risk(False),
        data_quality=0.95,
    )

    assert result["trade_intent"]["decision"] == "HOLD"
    assert "SENIOR_RISK_REJECT" in result["trade_intent"]["reason_codes"]


def test_settled_paper_outcome_is_recorded_for_training(tmp_path):
    result = build_paper_council(
        symbol="EURUSD",
        snapshot_id="snap-1",
        signal=_signal(),
        risk=_risk(),
        data_quality=0.95,
    )
    journal = CouncilTrainingJournal(str(tmp_path / "training.jsonl"))

    record = record_settled_paper_outcome(
        council=result["council"],
        trade_intent=result["trade_intent"],
        realized_direction="BUY",
        journal=journal,
    )

    assert record["execution_environment"] == "PAPER"
    assert record["broker_execution_allowed"] is False
    loaded = journal.load()
    assert len(loaded) == 1
    assert loaded[0].opinions[0]["agent"] == "technical"


def test_non_paper_or_broker_intent_cannot_enter_training_journal(tmp_path):
    result = build_paper_council(
        symbol="EURUSD",
        snapshot_id="snap-1",
        signal=_signal(),
        risk=_risk(),
        data_quality=0.95,
    )
    journal = CouncilTrainingJournal(str(tmp_path / "training.jsonl"))

    live_intent = dict(result["trade_intent"])
    live_intent["execution_environment"] = "LIVE"
    with pytest.raises(ValueError, match="PAPER"):
        record_settled_paper_outcome(
            council=result["council"],
            trade_intent=live_intent,
            realized_direction="BUY",
            journal=journal,
        )

    broker_intent = dict(result["trade_intent"])
    broker_intent["broker_execution_allowed"] = True
    with pytest.raises(ValueError, match="Broker-executed"):
        record_settled_paper_outcome(
            council=result["council"],
            trade_intent=broker_intent,
            realized_direction="BUY",
            journal=journal,
        )
