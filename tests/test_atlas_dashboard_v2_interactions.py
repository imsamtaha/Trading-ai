from app.dashboard.agent_panel import SCRIPT


def test_dashboard_v2_agent_panel_contains_ai_chat_and_chart_workspace():
    assert "ATLAS AI Chat" in SCRIPT
    assert "atlasChatInput" in SCRIPT
    assert "/agent/right-hand/chat" in SCRIPT
    assert "AI Chart" in SCRIPT
    assert "atlasChart" in SCRIPT
    assert "/dashboard/chart-data" in SCRIPT
    assert "chartIndicator" in SCRIPT


def test_dashboard_v2_chat_is_informational_not_execution_control():
    assert "Ask about markets, setups, risk, and ATLAS features" in SCRIPT
    assert "No order is sent from chat" in SCRIPT
