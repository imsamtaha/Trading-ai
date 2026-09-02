from datetime import datetime, timedelta, timezone

from app.atlas.access import resolve_atlas_access
from app.atlas.activation import activate_atlas


def active(plan="starter"):
    return {
        "status": "active",
        "plan_id": plan,
        "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


def test_active_subscription_gets_atlas_access():
    result = resolve_atlas_access(active("pro"), "starter")
    assert result.allowed is True
    assert result.plan_id == "pro"


def test_missing_subscription_is_blocked():
    result = resolve_atlas_access(None)
    assert result.allowed is False


def test_expired_subscription_is_blocked():
    subscription = active("starter")
    subscription["current_period_end"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    result = resolve_atlas_access(subscription)
    assert result.allowed is False


def test_buy_activation_requires_matching_approved_decision():
    result = activate_atlas(
        "BUY",
        {"action": "BUY", "approved": True},
        {"level": "LOW"},
        "paper",
    )
    assert result.status == "ACTIVATED"


def test_live_activation_is_blocked():
    result = activate_atlas(
        "BUY",
        {"action": "BUY", "approved": True},
        {"level": "LOW"},
        "live",
    )
    assert result.status == "BLOCKED"
