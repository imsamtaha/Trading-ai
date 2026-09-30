from __future__ import annotations


def test_private_plan_catalog_and_prices():
    from app.billing.plans import PLANS
    assert set(PLANS) == {"free", "starter", "pro", "elite"}
    assert PLANS["free"].monthly_price == 0
    assert PLANS["starter"].monthly_price == 99
    assert PLANS["pro"].monthly_price == 149
    assert PLANS["elite"].monthly_price == 299
    assert not any("Executive" in feature or "AI chart" in feature for feature in PLANS["free"].features)


def test_plan_features_keep_broker_execution_disabled():
    from app.billing.plans import access_for_plan
    for plan in ("FREE", "STARTER", "PRO", "ELITE"):
        access = access_for_plan(plan)
        assert access["mt5_demo_read_only"] is True
        assert access["broker_execution"] is False
        assert access["demo_executive"] is (plan != "FREE")


def test_private_dashboard_demo_executive_has_no_plan_or_locked_gate():
    from app.dashboard.views import DASHBOARD_HTML
    assert 'id="demoExecutivePanel"' in DASHBOARD_HTML
    assert 'data-plan-gated="demo_executive"' not in DASHBOARD_HTML
    assert 'id="liveExecutionSection"' not in DASHBOARD_HTML
    assert "Upgrade required for Demo Executive." not in DASHBOARD_HTML
    assert "LOCKED" not in DASHBOARD_HTML
    assert "/api/demo-executive/status" in DASHBOARD_HTML
    assert "/api/demo-executive/start" in DASHBOARD_HTML
    assert "/api/demo-executive/stop" in DASHBOARD_HTML


def test_private_dashboard_uses_automatic_demo_binding_copy():
    from app.dashboard.views import DASHBOARD_HTML
    assert ">ATLAS<" in DASHBOARD_HTML
    assert ">Trading Intelligence<" in DASHBOARD_HTML
    assert ">MT5 Demo<" in DASHBOARD_HTML
    assert "Verified Account" not in DASHBOARD_HTML
    assert "verified MT5 Demo" not in DASHBOARD_HTML


def test_private_dashboard_replaces_execution_gate_with_demo_engine_status():
    from app.dashboard.views import DASHBOARD_HTML
    assert "Execution Gate" not in DASHBOARD_HTML
    assert "Demo Engine" in DASHBOARD_HTML
    assert "el('execution').textContent='SIMULATION'" in DASHBOARD_HTML
