"""Regression coverage for PAPER-only Control Center navigation."""
from app.dashboard.trading_hub import HUB_HEADER, HUB_STYLE


def test_market_analysis_navigation_points_to_existing_market_section():
    assert 'href="#hub-markets"' in HUB_HEADER
    assert 'data-hub-en="Market Analysis"' in HUB_HEADER
    assert 'data-hub-ar="تحليل الأسواق"' in HUB_HEADER


def test_navigation_preserves_mobile_and_keyboard_accessibility():
    assert "min-height:44px" in HUB_STYLE
    assert "focus-visible" in HUB_STYLE
    assert "html[dir=rtl]" in HUB_STYLE


def test_no_order_execution_controls_added_to_navigation():
    assert "/order" not in HUB_HEADER
    assert "/trade/execute" not in HUB_HEADER
