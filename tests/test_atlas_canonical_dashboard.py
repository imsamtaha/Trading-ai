from app.dashboard import CANONICAL_ATLAS_PATH, _atlas_ultimate_html


def test_canonical_atlas_path_is_customer_entrypoint():
    assert CANONICAL_ATLAS_PATH == "/atlas-ultimate"


def test_canonical_dashboard_contains_market_intelligence_and_freshness_ui():
    html = _atlas_ultimate_html()

    assert "ATLAS Market Intelligence Boards" in html
    assert 'id="marketBoard"' in html
    assert 'id="headlines"' in html
    assert 'id="usable"' in html
    assert 'id="stale"' in html
    assert "freshness" in html
    assert "quote_time" in html
    assert "/dashboard/market-briefing" in html


def test_canonical_dashboard_contains_refresh_controls_and_preferences():
    html = _atlas_ultimate_html()

    assert 'id="refreshAll"' in html
    assert 'id="refreshBoards"' in html
    assert "window.refreshBriefing" in html
    assert '/ui/preferences.js' in html


def test_canonical_dashboard_preserves_manual_execution_boundary():
    html = _atlas_ultimate_html()

    assert "broker execution remains under the trader's control" in html
    assert "do not guarantee outcomes" in html
