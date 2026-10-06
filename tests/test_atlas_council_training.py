import json

import pytest

from app.intelligence.council import AgentOpinion, AtlasCouncilCoordinator
from app.intelligence.council_training import (
    AtlasCouncilTrainer,
    CouncilTrainingJournal,
    PaperTrainingExample,
    save_profile,
)
from app.intelligence.executive import AtlasExecutiveAgent


def _example(realized="BUY", technical="BUY", news="SELL"):
    return PaperTrainingExample(
        snapshot_id="snap-1",
        realized_direction=realized,
        opinions=(
            {"agent": "technical", "decision": technical, "confidence": 0.8},
            {"agent": "news", "decision": news, "confidence": 0.8},
        ),
    )


def test_trainer_keeps_agents_at_baseline_until_minimum_samples():
    profile = AtlasCouncilTrainer(minimum_samples=5).fit([_example() for _ in range(4)])

    assert profile["agents"]["technical"]["samples"] == 4
    assert profile["agents"]["technical"]["weight"] == 1.0
    assert profile["agents"]["technical"]["locked_baseline"] is True


def test_trainer_calibrates_reliable_and_unreliable_agents_after_enough_paper_outcomes():
    profile = AtlasCouncilTrainer(minimum_samples=5).fit([_example() for _ in range(8)])

    technical = profile["agents"]["technical"]
    news = profile["agents"]["news"]
    assert technical["locked_baseline"] is False
    assert news["locked_baseline"] is False
    assert technical["weight"] > 1.0
    assert news["weight"] < 1.0
    assert profile["training_environment"] == "PAPER"
    assert profile["broker_execution_allowed"] is False


def test_training_rejects_broker_or_non_paper_examples():
    with pytest.raises(ValueError, match="PAPER"):
        PaperTrainingExample(
            snapshot_id="snap-1",
            realized_direction="BUY",
            opinions=(),
            execution_environment="LIVE",
        )

    with pytest.raises(ValueError, match="Broker-executed"):
        PaperTrainingExample(
            snapshot_id="snap-1",
            realized_direction="BUY",
            opinions=(),
            broker_execution_allowed=True,
        )


def test_calibrated_profile_can_change_council_direction_without_enabling_broker_execution():
    profile = {
        "version": 1,
        "agents": {
            "technical": {"weight": 1.4},
            "news": {"weight": 0.6},
        },
    }
    council = AtlasCouncilCoordinator().build_package(
        symbol="EURUSD",
        snapshot_id="snap-1",
        opinions=[
            AgentOpinion("technical", "BUY", 0.55, (), "snap-1"),
            AgentOpinion("news", "SELL", 0.70, (), "snap-1"),
        ],
        senior_risk={"assessment": "RISK_ACCEPTABLE"},
        data_quality=0.95,
        agent_profile=profile,
    )
    result = AtlasExecutiveAgent().decide(council)

    assert council["calibration_active"] is True
    assert council["opinions"][0]["calibrated_confidence"] > council["opinions"][1]["calibrated_confidence"]
    assert result["decision"] == "BUY"
    assert result["execution_environment"] == "PAPER"
    assert result["broker_execution_allowed"] is False
    assert result["training_profile_version"] == 1


def test_training_journal_round_trip_and_profile_save(tmp_path):
    journal = CouncilTrainingJournal(str(tmp_path / "training.jsonl"))
    journal.append(_example())

    loaded = journal.load()
    assert len(loaded) == 1
    assert loaded[0].realized_direction == "BUY"

    profile = AtlasCouncilTrainer(minimum_samples=5).fit(loaded)
    target = save_profile(profile, str(tmp_path / "profile.json"))
    saved = json.loads(target.read_text(encoding="utf-8"))

    assert saved["total_examples"] == 1
    assert saved["agents"]["technical"]["weight"] == 1.0


def test_training_journal_rejects_nan(tmp_path):
    path = tmp_path / "training.jsonl"
    path.write_text(
        '{"snapshot_id":"s","realized_direction":"BUY","opinions":[],"data":NaN}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 1"):
        CouncilTrainingJournal(str(path)).load()
