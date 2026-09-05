from __future__ import annotations

import logging
import os
import secrets
import string
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.integrations.supabase_billing import SupabaseBillingError, SupabaseBillingJournal

try:
    import stripe
except ImportError:
    stripe = None


LOG = logging.getLogger("atlas.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


@dataclass(frozen=True)
class AtlasPlan:
    key: str
    name: str
    amount_usd: int
    price_env: str


PLANS = {
    "reader": AtlasPlan("reader", "ATLAS Reader", 49, "STRIPE_PRICE_READER"),
    "pro": AtlasPlan("pro", "ATLAS Pro Reader", 99, "STRIPE_PRICE_PRO"),
}


class BillingConfigurationError(RuntimeError):
    pass


def public_plans() -> list[dict[str, Any]]:
    return [
        {
            "key": plan.key,
            "name": plan.name,
            "amount_usd": plan.amount_usd,
            "trial_days": 3,
            "checkout_ready": bool(os.getenv(plan.price_env, "").strip()),
        }
        for plan in PLANS.values()
    ]


def _plan(key: str) -> AtlasPlan:
    plan = PLANS.get(key.lower())
    if plan is None:
        raise HTTPException(status_code=404, detail="Unknown subscription plan.")
    return plan


def _value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    getter = getattr(source, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(source, key, default)


def _client() -> Any:
    if stripe is None:
        raise BillingConfigurationError("Stripe SDK is not installed. Run pip install -r requirements.txt.")
    api_key = os.getenv("STRIPE_RESTRICTED_KEY", "").strip() or os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        raise BillingConfigurationError("STRIPE_RESTRICTED_KEY is not configured.")
    return stripe.StripeClient(api_key)


def _integration_identifier() -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    return "atlas_checkout_" + suffix


def create_checkout_session(plan_key: str, base_url: str) -> dict[str, str]:
    plan = _plan(plan_key)
    price_id = os.getenv(plan.price_env, "").strip()
    if not price_id:
        raise BillingConfigurationError(plan.price_env + " is not configured.")

    base = base_url.rstrip("/")
    session = _client().v1.checkout.sessions.create(
        {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": base + "/billing/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": base + "/subscribe",
            "allow_promotion_codes": True,
            "integration_identifier": _integration_identifier(),
            "metadata": {"atlas_plan": plan.key},
            "subscription_data": {
                "trial_period_days": 3,
                "metadata": {"atlas_plan": plan.key},
            },
        }
    )
    checkout_url = _value(session, "url")
    if not checkout_url:
        raise BillingConfigurationError("Stripe did not return a Checkout URL.")
    return {"checkout_url": str(checkout_url), "plan": plan.key}


def _billing_event(event: Any) -> dict[str, Any]:
    data = _value(_value(event, "data", {}), "object", {})
    event_type = str(_value(event, "type", "unknown"))
    subscription_id = _value(data, "subscription")
    if not subscription_id and event_type.startswith("customer.subscription."):
        subscription_id = _value(data, "id")
    metadata = _value(data, "metadata", {}) or {}
    customer_details = _value(data, "customer_details", {}) or {}
    return {
        "stripe_event_id": str(_value(event, "id", "")),
        "event_type": event_type,
        "plan": _value(metadata, "atlas_plan"),
        "customer_id": _value(data, "customer"),
        "subscription_id": subscription_id,
        "customer_email": _value(customer_details, "email") or _value(data, "customer_email"),
        "subscription_status": _value(data, "status") or _value(data, "payment_status"),
        "payload": {
            "livemode": bool(_value(event, "livemode", False)),
            "object_id": _value(data, "id"),
            "object_type": _value(data, "object"),
        },
    }


@router.post("/checkout/{plan_key}")
def checkout(plan_key: str, request: Request) -> dict[str, str]:
    base_url = os.getenv("ATLAS_PUBLIC_BASE_URL", "").strip() or str(request.base_url).rstrip("/")
    try:
        return create_checkout_session(plan_key, base_url)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Checkout creation failed.")
        raise HTTPException(status_code=502, detail="Unable to create checkout session.") from exc


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    signature = request.headers.get("stripe-signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not signature or not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured.")

    try:
        event = _client().construct_event(await request.body(), signature, webhook_secret)
    except Exception as exc:
        LOG.warning("Rejected Stripe webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from exc

    record = _billing_event(event)
    if not record["stripe_event_id"]:
        raise HTTPException(status_code=400, detail="Stripe event ID is missing.")
    try:
        SupabaseBillingJournal().record_event(**record)
    except SupabaseBillingError as exc:
        LOG.error("Billing event was not persisted: %s", exc)
        raise HTTPException(status_code=503, detail="Billing persistence is unavailable.") from exc
    return {"received": True}


@router.get("/success", response_class=HTMLResponse)
def billing_success() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang="en"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>ATLAS subscription received</title>
        <body style="margin:0;background:#07090e;color:#f3f5f7;font:16px system-ui;padding:48px">
        <main style="max-width:620px;margin:auto"><p style="color:#ff8a24;font-weight:800">ATLAS THE ULTIMATE</p>
        <h1>Subscription received.</h1>
        <p>Access activates after the signed billing event is recorded. ATLAS stays read-only for subscribers.</p>
        <p><a style="color:#ff8a24" href="/dashboard">Open dashboard</a></p>
        </main></body></html>"""
    )
