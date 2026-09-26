"""ATLAS subscription plans shared by the Whish payment flow."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    id: str
    name: str
    monthly_price: int
    trial_days: int
    features: tuple[str, ...]


PLANS: dict[str, SubscriptionPlan] = {
    "signals": SubscriptionPlan(
        id="signals",
        name="ATLAS Signals",
        monthly_price=99,
        trial_days=0,
        features=(
            "ATLAS sends trade signals",
            "Market dashboard and opportunity board",
            "Financial news context",
            "Risk notes for every signal",
        ),
    ),
    "execution": SubscriptionPlan(
        id="execution",
        name="ATLAS Execution",
        monthly_price=149,
        trial_days=0,
        features=(
            "Everything in ATLAS Signals",
            "ATLAS executes approved signals",
            "MT5 execution setup and monitoring",
            "Safety-gated account control after approval",
        ),
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())
