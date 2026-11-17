import pytest

from app.intelligence.seal_adapter import SEALModelInterface
from app.orchestrator import Orchestrator
from app.seal_bridge.feature_merge import LLMContextFeatures, TechnicalFeatures


class FakeConnector:
    def __init__(self):
        self.orders = []
        self.logs = []

    def read_account_state(self):
        return {"equity": 10_000.0, "server": "demo", "login": 123}

    def read_market_state(self, symbol, timeframe):
        return {"symbol": symbol, "timeframe": timeframe, "price": 1.1000, "atr_14": 0.0010}

    def place_order(self, proposal):
        self.orders.append(proposal)
        return {"status": "DRY_RUN", "proposal": proposal}

    def log_decision_cycle(self, payload):
        self.logs.append(payload)


class FakeFeaturePipeline:
    def build(self, market_state):
        return TechnicalFeatures(
            returns=[0.1, 0.2, -0.05],
            volatility=0.2,
            movement_modifier=1.0,
            regime_classification="trending",
            raw_features={
                "price": market_state["price"],
                "atr_14": market_state["atr_14"],
                "supporting_factors": ["structure", "trend_mtf", "momentum"],
                "counter_signals": ["minor resistance"],
                "data_quality_concerns": [],
            },
        )


class PassingModel(SEALModelInterface):
    def predict(self, model_input):
        return {
            "signal": "buy",
            "confidence": 0.76,
            "stop_loss_pips": 10,
            "take_profit_pips": 24,
        }


class HoldModel(SEALModelInterface):
    def predict(self, model_input):
        return {"signal": "hold", "confidence": 0.35}


class BadModel(SEALModelInterface):
    def predict(self, model_input):
        return {"signal": "buy", "confidence": 0.75}


class FakeLLMClient:
    def build_context(self, market_state):
        return LLMContextFeatures(
            sentiment_score=0.5,
            event_relevance=0.2,
            regime_hint="trending",
            branch_valid=True,
        )


def test_orchestrator_executes_only_after_seal_gate_and_risk_approval():
    connector = FakeConnector()
    orchestrator = Orchestrator(
        connector=connector,
        feature_pipeline=FakeFeaturePipeline(),
        seal_model=PassingModel(),
        llm_client=FakeLLMClient(),
        execution_enabled=True,
    )

    result = orchestrator.run_cycle("EURUSD", "15m")

    assert result["status"] == "EXECUTED"
    assert result["executor"]["executor_decision"] == "APPROVE_EXECUTION"
    assert len(connector.orders) == 1
    assert len(connector.logs) == 1


def test_orchestrator_does_not_execute_hold_signals():
    connector = FakeConnector()
    orchestrator = Orchestrator(
        connector=connector,
        feature_pipeline=FakeFeaturePipeline(),
        seal_model=HoldModel(),
        execution_enabled=True,
    )

    result = orchestrator.run_cycle("EURUSD", "15m")

    assert result["status"] == "BLOCKED"
    assert result["executor"]["executor_decision"] == "REJECT_EXECUTION"
    assert connector.orders == []
    assert len(connector.logs) == 1


def test_orchestrator_fails_loudly_on_invalid_model_output():
    orchestrator = Orchestrator(
        connector=FakeConnector(),
        feature_pipeline=FakeFeaturePipeline(),
        seal_model=BadModel(),
        execution_enabled=True,
    )

    with pytest.raises(ValueError, match="stop_loss_pips"):
        orchestrator.run_cycle("EURUSD", "15m")
