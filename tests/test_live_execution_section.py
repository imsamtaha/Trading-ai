from app.dashboard.views import DASHBOARD_HTML


def test_private_dashboard_omits_live_execution_controls():
    assert 'id="liveExecutionSection"' not in DASHBOARD_HTML
    assert 'id="demoExecutivePanel"' in DASHBOARD_HTML
    assert "Simulation only" in DASHBOARD_HTML
    assert "Demo Engine" in DASHBOARD_HTML
    assert "SIMULATION" in DASHBOARD_HTML
    assert "READ ONLY" not in DASHBOARD_HTML


def test_dashboard_has_mt5_fxpro_demo_connect_button():
    assert 'id="connectMt5FxPro"' in DASHBOARD_HTML
    assert '>Connect<' in DASHBOARD_HTML
    assert '/api/mt5-demo/connect' in DASHBOARD_HTML
