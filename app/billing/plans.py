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
        name="ATLAS Starter",
        monthly_price=99,
        trial_days=0,
        features=(
            "Live financial news board",
            "Market direction and bias",
            "AI chart workspace",
            "Editable indicators and setup context",
            "ATLAS AI question assistant",
        ),
    ),
    "reader": SubscriptionPlan(
        id="reader",
        name="ATLAS Pro",
        monthly_price=149,
        trial_days=0,
        features=(
            "Everything in Starter",
            "Live setup and signal overlays",
            "Entry/reference zones",
            "Targets and stop/invalidation levels",
            "Risk and confidence context",
            "Multi-asset opportunity matrix",
        ),
    ),
    "pro": SubscriptionPlan(
        id="pro",
        name="ATLAS Elite",
        monthly_price=299,
        trial_days=0,
        features=(
            "Everything in Pro",
            "Full ATLAS monitoring and analysis workflow",
            "Advanced risk and position monitoring",
            "Exit and stop alerts",
            "Priority intelligence briefings",
            "Advanced AI chart and assistant features",
        ),
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())
