import pytest

from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.executive import AtlasExecutiveAgent


def _council(risk="RISK_ACCEPTABLE", data_quality=0.95):
    return AtlasCouncilCoordinator().build_package(
        symbol="EURUSD",
        snapshot_id="snap-1",
        opinions=[
            AgentOpinion("technical", "BUY", 0.80, ("trend",), "snap-1"),
            AgentOpinion("news", "BUY", 0.70, ("macro",), "snap-1"),
            AgentOpinion("sentiment", "HOLD", 0.60, (), "snap-1"),
        ],
        senior_risk={"agent": "Senior Risk Management Agent", "assessment": risk},
        data_quality=data_quality,
    )


def test_executive_agent_produces_paper_only_trade_intent():
    result = AtlasExecutiveAgent().decide(_council())
    assert result["decision"] == "BUY"
    assert result["execution_environment"] == "PAPER"
    assert result["broker_execution_allowed"] is False


def test_senior_risk_reject_forces_hold():
    result = AtlasExecutiveAgent().decide(_council(risk="RISK_REJECT"))
    assert result["decision"] == "HOLD"
    assert "SENIOR_RISK_REJECT" in result["reason_codes"]


def test_low_data_quality_forces_hold():
    result = AtlasExecutiveAgent().decide(_council(data_quality=0.3))
    assert result["decision"] == "HOLD"
    assert "LOW_DATA_QUALITY" in result["reason_codes"]


def test_council_rejects_stale_agent_snapshot():
    with pytest.raises(ValueError, match="snapshot_id"):
        AtlasCouncilCoordinator().build_package(
            symbol="EURUSD",
            snapshot_id="new",
            opinions=[AgentOpinion("technical", "BUY", 0.8, (), "old")],
            senior_risk={"assessment": "RISK_ACCEPTABLE"},
            data_quality=0.9,
        )
