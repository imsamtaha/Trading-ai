from app.billing.plans import PLANS


def test_signals_plan_is_99_and_manual_execution_only():
    plan = PLANS["watch"]
    assert plan.name == "ATLAS Signals & Setups"
    assert plan.monthly_price == 99
    assert "Telegram and email signal delivery" in plan.features
    assert "Manual execution by the customer" in plan.features


def test_council_plan_is_149_and_requires_human_confirmation():
    plan = PLANS["reader"]
    assert plan.name == "ATLAS Council"
    assert plan.monthly_price == 149
    assert "Council-generated trade intents" in plan.features
    assert "Human confirmation before execution" in plan.features


def test_elite_plan_price_remains_299():
    plan = PLANS["pro"]
    assert plan.name == "ATLAS Elite"
    assert plan.monthly_price == 299
