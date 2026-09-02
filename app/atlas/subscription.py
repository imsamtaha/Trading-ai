from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AtlasPlan:
    id: str
    name: str
    monthly_price: int
    features: tuple[str, ...]


PLANS = (
    AtlasPlan(
        id="starter",
        name="STARTER",
        monthly_price=29,
        features=("dashboard", "market_watch", "atlas", "mtf", "basic_risk", "paper_trading"),
    ),
    AtlasPlan(
        id="pro",
        name="PRO",
        monthly_price=59,
        features=("dashboard", "market_watch", "atlas", "mtf", "advanced_risk", "paper_trading", "demo_mt5", "alerts"),
    ),
    AtlasPlan(
        id="elite",
        name="ELITE",
        monthly_price=99,
        features=("dashboard", "market_watch", "atlas", "mtf", "advanced_risk", "paper_trading", "demo_mt5", "advanced_analytics", "portfolio_intelligence"),
    ),
)


def get_plan(plan_id: str) -> AtlasPlan | None:
    plan_id = plan_id.lower()
    return next((plan for plan in PLANS if plan.id == plan_id), None)
