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
    "watch": SubscriptionPlan(
        id="watch",
        name="ATLAS Market Watch",
        monthly_price=29,
        trial_days=0,
        features=(
            "Live financial news board",
            "Market direction and bias",
            "Market structure analysis",
            "Key levels and strategy context",
        ),
    ),
    "reader": SubscriptionPlan(
        id="reader",
        name="ATLAS Signals",
        monthly_price=49,
        trial_days=0,
        features=(
            "Everything in Market Watch",
            "Manual-execution market signals",
            "Entry/reference zones",
            "Targets and stop/invalidation levels",
            "Risk and confidence context",
        ),
    ),
    "pro": SubscriptionPlan(
        id="pro",
        name="ATLAS Pro",
        monthly_price=99,
        trial_days=0,
        features=(
            "Everything in Signals",
            "Full ATLAS monitoring and analysis workflow",
            "Multi-asset opportunity matrix",
            "Risk and position monitoring",
            "Exit and stop alerts",
            "Priority intelligence briefings",
        ),
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())
