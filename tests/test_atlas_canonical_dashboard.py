from app.dashboard import CANONICAL_ATLAS_PATH, _atlas_ultimate_html
from app.dashboard.preferences import SCRIPT


def test_canonical_atlas_path_is_customer_entrypoint():
    assert CANONICAL_ATLAS_PATH == "/"


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
    assert "demo/read-only" in html.lower()
    assert "does not guarantee trading outcomes" in html


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


def test_canonical_dashboard_is_trading_hub_with_section_navigation():
    html = _atlas_ultimate_html()
    assert "TRADING INTELLIGENCE" in html
    assert 'class="atlas-hub-nav"' in html
    for target in ("#hub-overview", "#hub-account", "#hub-markets", "#demo-session", "#plans"):
        assert f'href="{target}"' in html


def test_trading_hub_has_premium_3d_and_mobile_ui_hooks():
    html = _atlas_ultimate_html()
    assert "atlas-hub-shell" in html
    assert "atlas-3d" in html
    assert "focus-visible" in html
    assert "min-height:44px" in html
    assert "@media(max-width:700px)" in html


def test_trading_hub_localizes_demo_panel_and_keeps_paper_boundary():
    html = _atlas_ultimate_html()
    required = (
        "FORWARD DEMO VALIDATION",
        "ATLAS Demo Trading",
        "Open Paper Trades",
        "Closed Trades",
        "Review Target",
        "Profit Factor",
        "Expectancy",
        "Drawdown / Risk",
        "Latest Demo Events",
        "Live Readiness Gate",
        "Performance Center",
        "No broker orders",
    )
    for phrase in required:
        assert phrase in html
    assert "تداول تجريبي" in html
    assert "لا أوامر للوسيط" in html


def test_canonical_page_does_not_inject_duplicate_refresh_all_control():
    html = _atlas_ultimate_html()
    assert "actions.prepend(all)" not in html
