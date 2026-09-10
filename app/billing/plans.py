"""ATLAS subscription plans shared by the payment flows."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    id: str
    name: str
    monthly_price: int
    trial_days: int
    features: tuple[str, ...]


PLANS: dict[str, SubscriptionPlan] = {
    "reader": SubscriptionPlan(
        id="reader",
        name="ATLAS Reader",
        monthly_price=49,
        trial_days=0,
        features=(
            "Read-only MT5 cockpit",
            "Wall Street board",
            "Financial news",
            "Demo performance reports",
        ),
    ),
    "pro": SubscriptionPlan(
        id="pro",
        name="ATLAS Pro Reader",
        monthly_price=99,
        trial_days=0,
        features=(
            "Everything in Reader",
            "Expanded multi-asset opportunity matrix",
            "Advanced risk reports",
            "Priority subscriber briefings",
        ),
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())
