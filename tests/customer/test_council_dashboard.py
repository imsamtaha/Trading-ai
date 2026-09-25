from fastapi.testclient import TestClient
from app.dashboard import atlas_ultimate_view
from app.main import app

client = TestClient(app)


def test_dashboard_contains_realtime_council_panel_and_script():
    html = atlas_ultimate_view().body.decode()
    assert "ATLAS Intelligence Council" in html
    assert "/ui/customer-v2-panel.js" in html


def test_customer_panel_script_reads_v2_state_using_existing_auth_session():
    response = client.get("/ui/customer-v2-panel.js")
    assert response.status_code == 200
    text = response.text
    assert "window.atlasAuth" in text
    assert "/api/v2/customer/agents/status" in text
    assert "/api/v2/customer/decisions/latest" in text
    assert "/api/v2/customer/rescue/status" in text
