from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.risk_reference import risk_reference_manifest, risk_study_topic, risk_study_topics


def test_risk_v3_reference_is_a_read_only_study_index():
    manifest = risk_reference_manifest()
    assert manifest["source_pages"] == 40
    assert manifest["scope"] == "PAPER_EDUCATION_ONLY"
    assert manifest["affects_risk_policy"] is False
    assert manifest["broker_execution_allowed"] is False
    assert len(risk_study_topics()) == 9
    assert risk_study_topic("trident")["pages"] == "27-29"
    assert risk_study_topic("missing") is None


def test_council_attaches_reference_without_changing_risk_result():
    original = {"approved": False, "assessment": "RISK_REJECT", "reason": "Test veto"}
    council = AtlasCouncilCoordinator().build_package(
        symbol="TEST",
        snapshot_id="test-study-only",
        opinions=[AgentOpinion(agent="technical", decision="HOLD", confidence=0.7)],
        senior_risk=original,
        data_quality=1.0,
    )
    assert council["senior_risk_management"]["assessment"] == "RISK_REJECT"
    assert council["risk_education_reference"] == risk_reference_manifest()
    assert original["assessment"] == "RISK_REJECT"
