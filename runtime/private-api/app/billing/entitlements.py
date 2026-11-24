"""Owner-verified Whish subscription entitlement checks."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

PAID_PLANS = {"STARTER", "PRO", "ELITE"}


def paid_access(subscription: dict[str, Any] | None, now: datetime | None = None) -> bool:
    if not subscription:
        return False
    if str(subscription.get("plan", "")).upper() not in PAID_PLANS:
        return False
    if str(subscription.get("status", "")).upper() != "ACTIVE":
        return False
    if not str(subscription.get("billing_reference") or "").startswith("ATLAS-"):
        return False
    try:
        expiry = datetime.fromisoformat(str(subscription.get("expires_at") or ""))
        return expiry.tzinfo is not None and expiry > (now or datetime.now(timezone.utc))
    except ValueError:
        return False
