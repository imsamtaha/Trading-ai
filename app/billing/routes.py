from app.billing.plans import public_plans
from app.billing.whish import settings as whish_settings
from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/methods")
def payment_methods() -> dict:
    return {
        "whish": {
            "available": whish_settings()["available"],
            "mode": "manual_review",
        }
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
