from app.billing.plans import PLANS


def test_customer_plans_use_v2_names_and_prices():
    assert PLANS["watch"].name == "ATLAS Signals & Setups"
    assert PLANS["watch"].monthly_price == 99
    assert PLANS["reader"].name == "ATLAS Council"
    assert PLANS["reader"].monthly_price == 149
    assert PLANS["pro"].name == "ATLAS Elite"
    assert PLANS["pro"].monthly_price == 299
    assert all(plan.trial_days == 0 for plan in PLANS.values())
