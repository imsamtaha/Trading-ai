from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AtlasAccess:
    allowed: bool
    plan_id: str | None
    reason: str


ACTIVE_STATUSES = {"active", "trialing"}


def resolve_atlas_access(subscription: dict[str, Any] | None, required_plan: str = "starter") -> AtlasAccess:
    """Resolve access using trusted server-side subscription state."""
    if not subscription:
        return AtlasAccess(False, None, "active subscription required")

    status = str(subscription.get("status", "")).lower()
    plan_id = str(subscription.get("plan_id", "")).lower() or None
    if status not in ACTIVE_STATUSES:
        return AtlasAccess(False, plan_id, f"subscription status is {status or 'unknown'}")

    expires = subscription.get("current_period_end")
    if expires:
        try:
            expiry = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if expiry <= datetime.now(timezone.utc):
                return AtlasAccess(False, plan_id, "subscription period has ended")
        except ValueError:
            return AtlasAccess(False, plan_id, "invalid subscription period")

    rank = {"starter": 1, "pro": 2, "elite": 3}
    if rank.get(plan_id, 0) < rank.get(required_plan.lower(), 1):
        return AtlasAccess(False, plan_id, "subscription plan does not include this ATLAS feature")

    return AtlasAccess(True, plan_id, "ATLAS access granted")
