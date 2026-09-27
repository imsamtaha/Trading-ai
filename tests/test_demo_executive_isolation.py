from __future__ import annotations

import pytest


class FakeMT5DemoService:
    def get_dashboard_state(self, user_id):
        return {
            "connected": True,
            "account": {"account_type": "DEMO", "account_masked": "***1234"},
            "symbols": [{
                "symbol": "EURUSD",
                "canonical_symbol": "EURUSD",
                "trend": "BULLISH",
                "confidence": 80.0,
                "risk_level": "LOW",
                "opportunity_score": 90.0,
                "price": 1.1,
            }],
            "positions": [],
            "pending_orders": [],
            "recent_trades": [],
        }


def make_repo():
    from app.users.repository import MemoryUserRepository
    repo = MemoryUserRepository()
    repo.get_or_create_profile("free-user")
    repo.get_or_create_profile("pro-user")
    repo.subscriptions["pro-user"] = {"user_id": "pro-user", "plan": "PRO", "status": "ACTIVE"}
    return repo


def test_free_user_cannot_start_demo_executive():
    from app.demo_executive.service import DemoExecutiveAccessError, DemoExecutiveService
    service = DemoExecutiveService(make_repo(), FakeMT5DemoService())
    with pytest.raises(DemoExecutiveAccessError):
        service.start("free-user")


def test_paid_user_events_are_isolated_and_simulation_only(monkeypatch):
    from app.demo_executive.service import DemoExecutiveService
    from app.execution.mt5 import MT5Broker

    def forbidden_order(*args, **kwargs):
        raise AssertionError("broker execution must not be reached")

    monkeypatch.setattr(MT5Broker, "market_order", forbidden_order)
    repo = make_repo()
    service = DemoExecutiveService(repo, FakeMT5DemoService())
    result = service.start("pro-user")
    assert result["active"] is True
    events = service.events("pro-user")
    assert len(events) == 1
    assert events[0]["decision"] in {"SIMULATE_BUY", "SIMULATE_SELL", "WAIT"}
    assert events[0]["simulation_only"] is True
    assert service.events("free-user") == []


def test_stop_records_close_simulation_for_active_user():
    from app.demo_executive.service import DemoExecutiveService
    repo = make_repo()
    service = DemoExecutiveService(repo, FakeMT5DemoService())
    service.start("pro-user")
    result = service.stop("pro-user")
    assert result["active"] is False
    assert service.events("pro-user")[-1]["decision"] == "CLOSE_SIMULATION"
