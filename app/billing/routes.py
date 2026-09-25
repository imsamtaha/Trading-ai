import os

from app.billing.plans import public_plans
from app.billing.whish import settings as whish_settings
from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])


def _stripe_links() -> dict[str, str]:
    links = {}
    for plan in ("reader", "pro"):
        value = os.getenv(f"ATLAS_STRIPE_LINK_{plan.upper()}", "").strip()
        if value.startswith("https://buy.stripe.com/"):
            links[plan] = value
    return links


@router.get("/methods")
def payment_methods() -> dict:
    links = _stripe_links()
    whish = whish_settings()
    return {
        "stripe": {
            "provider": "Stripe",
            "available": len(links) == 2,
            "mode": "live_checkout" if len(links) == 2 else "account_activation_or_checkout_pending",
            "plans": sorted(links.keys()),
            "required_plans": ["reader", "pro"],
            "unsupported_plans": ["watch"],
        },
        "whish": {
            "provider": "Whish Pay",
            "available": whish["available"],
            "mode": "manual_review" if whish["available"] else "merchant_activation_pending",
            "checkout_type": "wallet_payment_gateway",
        },
    }


@router.get("/plans")
def plans() -> dict:
    return {
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "monthly_price": plan.monthly_price,
                "trial_days": plan.trial_days,
                "features": list(plan.features),
            }
            for plan in public_plans()
        ]
    }
