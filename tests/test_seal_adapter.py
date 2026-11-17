import pytest

from app.intelligence.seal_adapter import ExecutionGatekeeper, SEALModelInterface, UnimplementedSEALModel


class BadDirectionalModel(SEALModelInterface):
    def predict(self, model_input):
        return {"signal": "buy", "confidence": 0.72}


class ValidHoldModel(SEALModelInterface):
    def predict(self, model_input):
        return {"signal": "hold", "confidence": 0.31}


def test_unimplemented_seal_model_fails_loudly():
    with pytest.raises(NotImplementedError):
        UnimplementedSEALModel().predict_and_validate({})


def test_directional_signal_requires_real_stop_and_target():
    with pytest.raises(ValueError, match="stop_loss_pips"):
        BadDirectionalModel().predict_and_validate({})


def test_hold_signal_validates_without_stop_or_target():
    output = ValidHoldModel().predict_and_validate({})

    assert output["signal"] == "hold"
    assert output["confidence"] == 0.31


def test_gate_rejects_directional_signal_with_fewer_than_three_confirmations():
    result = ExecutionGatekeeper().evaluate(
        {
            "signal": "buy",
            "confidence": 0.74,
            "stop_loss_pips": 18,
            "take_profit_pips": 36,
            "supporting_factors": ["trend_mtf", "momentum"],
            "counter_signals": ["nearby resistance"],
            "data_quality_concerns": [],
        }
    )

    assert result["executor_decision"] == "REJECT_EXECUTION"
    assert "Fewer than 3 independent confirmations." in result["execution_blockers"]


def test_gate_requires_human_review_when_confirmations_pass_but_data_is_concerning():
    result = ExecutionGatekeeper().evaluate(
        {
            "signal": "sell",
            "confidence": 0.76,
            "stop_loss_pips": 12,
            "take_profit_pips": 30,
            "supporting_factors": ["structure", "trend_mtf", "momentum"],
            "counter_signals": ["short-term support below price"],
            "data_quality_concerns": ["volume unavailable from broker feed"],
        }
    )

    assert result["executor_decision"] == "REQUIRE_HUMAN_REVIEW"
    assert result["required_confirmations_met"] is True
    assert result["human_review_required"] is True


def test_gate_approves_only_after_confirmation_stop_target_and_context_checks():
    result = ExecutionGatekeeper().evaluate(
        {
            "signal": "buy",
            "confidence": 0.8,
            "stop_loss_pips": 20,
            "take_profit_pips": 45,
            "supporting_factors": ["structure", "trend_mtf", "liquidity", "momentum"],
            "counter_signals": ["minor intraday resistance"],
            "data_quality_concerns": [],
        },
        market_context={
            "spread_ok": True,
            "volatility_ok": True,
            "session_ok": True,
            "high_impact_news": False,
        },
    )

    assert result["executor_decision"] == "APPROVE_EXECUTION"
    assert result["execution_blockers"] == []
    assert result["required_confirmations_met"] is True
