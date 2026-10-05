from app import dashboard as dashboard_module


def test_mt5_state_forces_read_only(monkeypatch):
    import app.dashboard.api as dashboard_api

    monkeypatch.setattr(
        dashboard_api,
        "atlas_dashboard_state",
        lambda: {
            "mode": "LIVE_EXECUTION",
            "services": {
                "mt5": "ONLINE",
                "execution_gate": "ENABLED",
            },
            "account": {"account_type": "DEMO"},
            "symbols": [],
            "positions": [],
            "open_positions": 0,
        },
    )

    state = dashboard_module.mt5_state()

    assert state["mode"] == "READ_ONLY"
    assert state["execution"] == "disabled"
    assert state["services"]["execution_gate"] == "DISABLED"
    assert state["services"]["subscriber_access"] == "READ_ONLY"


def test_dashboard_source_has_no_merge_conflict_markers():
    source = dashboard_module.__file__
    with open(source, "r", encoding="utf-8") as handle:
        text = handle.read()

    assert "<<<<<<<" not in text
    assert ">>>>>>>" not in text
    assert "=======" not in text


def test_mt5_state_preserves_broker_demo_telemetry(monkeypatch):
    import app.dashboard.api as dashboard_api

    monkeypatch.setenv("ATLAS_LIVE_DEMO", "true")
    monkeypatch.setattr(
        dashboard_api,
        "atlas_dashboard_state",
        lambda: {
            "mode": "BROKER_DEMO_CONFIGURED",
            "services": {
                "mt5": "ONLINE",
                "execution_gate": "DEMO_BROKER",
            },
            "account": {"account_type": "DEMO"},
            "symbols": [],
            "positions": [],
            "open_positions": 0,
        },
    )

    state = dashboard_module.mt5_state()

    assert state["mode"] == "BROKER_DEMO_CONFIGURED"
    assert state["execution"] == "broker_demo"
    assert state["services"]["execution_gate"] == "DEMO_BROKER"
    assert state["services"]["subscriber_access"] == "LIVE_DEMO"
