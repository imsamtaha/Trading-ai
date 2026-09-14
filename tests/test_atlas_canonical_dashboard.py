from app.dashboard import CANONICAL_ATLAS_PATH, _atlas_ultimate_html
from app.dashboard.preferences import SCRIPT


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


def test_arabic_preferences_cover_dynamic_market_labels():
    required = {
        "ATLAS Market Intelligence Boards": "لوحات ذكاء الأسواق من ATLAS",
        "Breadth": "اتساع السوق",
        "Rising": "الأسواق الصاعدة",
        "Falling": "الأسواق المتراجعة",
        "Tracked": "الأسواق المتابعة",
        "Usable": "بيانات صالحة للتحليل",
        "Stale": "بيانات قديمة",
        "FRESH": "محدّثة",
        "DELAYED": "متأخرة",
        "STALE": "قديمة",
        "UNAVAILABLE": "غير متاح",
        "No quote time": "وقت السعر غير متاح",
        "Quote": "وقت السعر",
    }
    for english, arabic in required.items():
        assert f"'{english}':'{arabic}'" in SCRIPT


def test_language_change_triggers_only_one_briefing_refresh_path():
    onchange = SCRIPT.split("bar.querySelector('#atlas-lang').onchange=e=>", 1)[1].split(";bar.querySelector('#atlas-theme')", 1)[0]

    assert "atlas-language-change" in onchange
    assert "window.refreshBriefing" not in onchange
