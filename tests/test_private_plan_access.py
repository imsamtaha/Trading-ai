from __future__ import annotations


def test_private_plan_catalog_and_prices():
    from app.billing.plans import PLANS
    assert set(PLANS) == {"free", "starter", "pro", "elite"}
    assert PLANS["free"].monthly_price == 0
    assert PLANS["starter"].monthly_price == 99
    assert PLANS["pro"].monthly_price == 149
    assert PLANS["elite"].monthly_price == 299


def test_plan_features_keep_broker_execution_disabled():
    from app.billing.plans import access_for_plan
    for plan in ("FREE", "STARTER", "PRO", "ELITE"):
        access = access_for_plan(plan)
        assert access["mt5_demo_read_only"] is True
        assert access["broker_execution"] is False
    assert access_for_plan("FREE")["demo_executive"] is False
    for plan in ("STARTER", "PRO", "ELITE"):
        assert access_for_plan(plan)["demo_executive"] is True


def test_private_dashboard_contains_demo_executive_plan_gate():
    from app.dashboard.views import DASHBOARD_HTML
    assert 'id="demoExecutivePanel"' in DASHBOARD_HTML
    assert 'data-plan-gated="demo_executive"' in DASHBOARD_HTML
    assert "/api/demo-executive/status" in DASHBOARD_HTML
    assert "/api/demo-executive/start" in DASHBOARD_HTML
    assert "/api/demo-executive/stop" in DASHBOARD_HTML
