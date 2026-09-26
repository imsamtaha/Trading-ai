from app.dashboard.preferences import SCRIPT
from app.dashboard.views import DASHBOARD_HTML


def test_dashboard_has_gold_technical_typography_and_demo_trade_panel():
    assert '--gold:' in DASHBOARD_HTML
    assert 'Rajdhani' in DASHBOARD_HTML
    for token in ('id="assetSelect"', 'id="assetPrice"', 'id="demoPosition"'):
        assert token in DASHBOARD_HTML
    assert 'data-demo-action="BUY"' in DASHBOARD_HTML
    assert 'data-demo-action="SELL"' in DASHBOARD_HTML


def test_dashboard_arabic_covers_live_demo_trade_ui():
    for pair in (
        "'Live Demo Trading':'التداول التجريبي المباشر'",
        "'Asset':'الأصل'",
        "'Current Price':'السعر الحالي'",
        "'Buy Demo':'شراء تجريبي'",
        "'Sell Demo':'بيع تجريبي'",
        "'Close Demo Position':'إغلاق الصفقة التجريبية'",
        "'score':'النتيجة'",
        "'confidence':'الثقة'",
        "'opportunity':'الفرصة'",
    ):
        assert pair in SCRIPT
    assert "document.documentElement.dir=lang==='ar'?'rtl':'ltr'" in SCRIPT


def test_dashboard_has_ai_chart_and_main_atlas_logo():
    assert 'id="atlasLogo"' in DASHBOARD_HTML
    assert 'data:image/webp;base64,' in DASHBOARD_HTML
    assert 'id="atlasAiChart"' in DASHBOARD_HTML
    assert 'AI Chart' in DASHBOARD_HTML
    assert 'id="aiTimeframe"' in DASHBOARD_HTML
    for token in ('AI Trend', 'AI Momentum', 'AI Signal', 'AI Confidence'):
        assert token in DASHBOARD_HTML


def test_arabic_covers_ai_chart_labels():
    for pair in (
        "'AI Chart':'الرسم البياني بالذكاء الاصطناعي'",
        "'AI Trend':'اتجاه الذكاء الاصطناعي'",
        "'AI Momentum':'زخم الذكاء الاصطناعي'",
        "'AI Signal':'إشارة الذكاء الاصطناعي'",
        "'AI Confidence':'ثقة الذكاء الاصطناعي'",
        "'Timeframe':'الإطار الزمني'",
    ):
        assert pair in SCRIPT
