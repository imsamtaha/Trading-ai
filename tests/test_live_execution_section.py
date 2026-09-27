from app.dashboard.views import DASHBOARD_HTML


def test_dashboard_has_locked_live_execution_section():
    assert 'id="liveExecutionSection"' in DASHBOARD_HTML
    assert 'Live Execution' in DASHBOARD_HTML
    assert 'LOCKED' in DASHBOARD_HTML
    assert 'Broker execution: OFF' in DASHBOARD_HTML


def test_dashboard_has_mt5_fxpro_demo_connect_button():
    assert 'id="connectMt5FxPro"' in DASHBOARD_HTML
    assert 'Connect MT5 FxPro Demo' in DASHBOARD_HTML
    assert '/api/mt5-demo/connect' in DASHBOARD_HTML
