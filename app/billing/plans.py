from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    id: str
    name: str
    monthly_price: int
    trial_days: int
    features: tuple[str, ...]


PLANS: dict[str, SubscriptionPlan] = {
    "free": SubscriptionPlan(
        id="free", name="ATLAS Free", monthly_price=0, trial_days=0,
        features=("Private account", "FxPro MT5 Demo or Real connection", "Read-only account telemetry", "Public market preview"),
    ),
    "starter": SubscriptionPlan(
        id="starter", name="ATLAS Starter", monthly_price=99, trial_days=0,
        features=("Everything in Free", "Live Demo Executive simulation", "Alerts", "Extended analytics"),
    ),
    "pro": SubscriptionPlan(
        id="pro", name="ATLAS Pro", monthly_price=149, trial_days=0,
        features=("Everything in Starter", "Deeper analytics", "Longer activity history", "Priority support"),
    ),
    "elite": SubscriptionPlan(
        id="elite", name="ATLAS Elite", monthly_price=299, trial_days=0,
        features=("Everything in Pro", "Advanced monitoring", "Expanded history", "Premium support"),
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())


def access_for_plan(plan: str) -> dict[str, bool]:
    normalized = str(plan or "FREE").upper()
    return {
        "mt5_demo_read_only": normalized in {"FREE", "STARTER", "PRO", "ELITE"},
        "demo_executive": normalized in {"STARTER", "PRO", "ELITE"},
        "broker_execution": False,
        "private_dashboard": normalized in {"FREE", "STARTER", "PRO", "ELITE"},
    }
