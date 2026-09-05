def test_dashboard_module_imports_without_metatrader5_on_ci():
    import app.dashboard.api as dashboard_api

    assert callable(dashboard_api.market_briefing)
