"""Stripe Checkout and webhook helpers for fixed-price ATLAS subscriptions.

All payment calls run server-side. The browser receives only the hosted Checkout
URL. Stripe's dynamic payment methods are intentionally left enabled: this
module never passes payment_method_types.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import requests


STRIPE_API_VERSION = "2026-07-29.dahlia"


class BillingConfigurationError(RuntimeError):
    """Raised when a required production billing setting is missing."""


class BillingProviderError(RuntimeError):
    """Raised when Stripe or the audit store rejects a billing operation."""


@dataclass(frozen=True)
class SubscriptionPlan:
    id: str
    name: str
    monthly_price: int
    trial_days: int
    features: tuple[str, ...]
    price_env: str


PLANS: dict[str, SubscriptionPlan] = {
    "reader": SubscriptionPlan(
        id="reader",
        name="ATLAS Reader",
        monthly_price=49,
        trial_days=3,
        features=(
            "Read-only MT5 cockpit",
            "Wall Street board",
            "Financial news",
            "Demo performance reports",
        ),
        price_env="ATLAS_STRIPE_PRICE_READER",
    ),
    "trader": SubscriptionPlan(
        id="trader",
        name="ATLAS Trader",
        monthly_price=99,
        trial_days=3,
        features=(
            "Everything in Reader",
            "Demo MT5 connector",
            "Advanced risk reports",
            "Live execution eligibility after risk approval",
        ),
        price_env="ATLAS_STRIPE_PRICE_TRADER",
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())


class StripeBilling:
    """Create hosted subscription Checkout Sessions and audit verified webhooks."""

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        webhook_secret: str | None = None,
        app_url: str | None = None,
        supabase_url: str | None = None,
        supabase_service_role_key: str | None = None,
    ) -> None:
        self.secret_key = (secret_key if secret_key is not None else os.getenv("STRIPE_SECRET_KEY", "")).strip()
        self.webhook_secret = (
            webhook_secret if webhook_secret is not None else os.getenv("STRIPE_WEBHOOK_SECRET", "")
        ).strip()
        self.app_url = (app_url if app_url is not None else os.getenv("ATLAS_APP_URL", "")).rstrip("/")
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.getenv("SUPABASE_URL", "")
        ).rstrip("/")
        self.supabase_service_role_key = (
            supabase_service_role_key
            if supabase_service_role_key is not None
            else os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip()

    def checkout_configured(self, plan_id: str) -> bool:
        plan = self.plan(plan_id)
        return bool(self.secret_key and self.app_url and os.getenv(plan.price_env, "").strip())

    def plan(self, plan_id: str) -> SubscriptionPlan:
        try:
            return PLANS[plan_id]
        except KeyError as exc:
            raise BillingConfigurationError("Unknown subscription plan.") from exc

    def create_checkout_session(
        self,
        plan_id: str,
        *,
        user_id: str | None = None,
        customer_email: str | None = None,
    ) -> dict[str, str]:
        plan = self.plan(plan_id)
        price_id = os.getenv(plan.price_env, "").strip()
        if not self.secret_key or not self.app_url or not price_id:
            raise BillingConfigurationError(
                f"Billing for {plan.name} is not configured. Set STRIPE_SECRET_KEY, "
                f"ATLAS_APP_URL, and {plan.price_env}."
            )

        metadata = {"atlas_plan": plan.id}
        if user_id:
            metadata["atlas_user_id"] = user_id

        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "subscription_data": {
                "trial_period_days": plan.trial_days,
                "metadata": metadata,
            },
            "metadata": metadata,
            "success_url": f"{self.app_url}/subscribe?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{self.app_url}/subscribe?checkout=cancelled",
            "integration_identifier": f"atlas_checkout_{secrets.token_hex(4)}",
        }
        if customer_email:
            params["customer_email"] = customer_email

        try:
            session = self._client().v1.checkout.sessions.create(params=params)
        except Exception as exc:  # Stripe exception types require the optional SDK at runtime.
            raise BillingProviderError("Stripe could not create the Checkout Session.") from exc

        session_id = _field(session, "id")
        session_url = _field(session, "url")
        if not session_id or not session_url:
            raise BillingProviderError("Stripe returned an incomplete Checkout Session.")

        return {"id": str(session_id), "url": str(session_url), "plan_id": plan.id}

    def construct_event(self, payload: bytes, signature: str) -> Any:
        if not self.webhook_secret:
            raise BillingConfigurationError("STRIPE_WEBHOOK_SECRET is required for webhook verification.")
        if not signature:
            raise BillingProviderError("Missing Stripe signature.")

        try:
            return self._client().construct_event(payload, signature, self.webhook_secret)
        except Exception as exc:  # The SDK verifies the timestamp and signature.
            raise BillingProviderError("Stripe webhook signature verification failed.") from exc

    def record_verified_event(self, event: Any) -> None:
        """Persist the minimal verified event record; never store payment secrets."""
        if not self.supabase_url or not self.supabase_service_role_key:
            raise BillingConfigurationError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for billing audit persistence."
            )

        event_type = str(_field(event, "type") or "")
        event_id = str(_field(event, "id") or "")
        data = _field(event, "data", {})
        obj = _field(data, "object", {})
        metadata = _field(obj, "metadata", {}) or {}
        if not isinstance(metadata, Mapping):
            metadata = {}

        plan_id = str(metadata.get("atlas_plan") or "") or None
        user_id = str(metadata.get("atlas_user_id") or "") or None
        customer_details = _field(obj, "customer_details", {}) or {}
        email = _field(customer_details, "email") or _field(obj, "customer_email")
        provider_subscription_id = _field(obj, "subscription") or _field(obj, "id")
        provider_customer_id = _field(obj, "customer")
        status = _field(obj, "status") or _subscription_status_for_event(event_type)

        if not event_id or not event_type:
            raise BillingProviderError("Stripe webhook did not include a valid event id and type.")

        row = {
            "provider": "stripe",
            "provider_event_id": event_id,
            "event_type": event_type,
            "user_id": user_id,
            "email": email,
            "plan_id": plan_id,
            "provider_customer_id": provider_customer_id,
            "provider_subscription_id": provider_subscription_id,
            "status": status,
            "payload": {
                "livemode": bool(_field(event, "livemode", False)),
                "payment_status": _field(obj, "payment_status"),
                "trial_end": _field(obj, "trial_end"),
            },
        }
        response = requests.post(
            f"{self.supabase_url}/rest/v1/billing_events?on_conflict=provider_event_id",
            headers=self._supabase_headers("resolution=ignore"),
            json=row,
            timeout=15,
        )
        if not response.ok:
            raise BillingProviderError(f"Billing audit persistence failed ({response.status_code}).")

        if user_id and plan_id and provider_subscription_id:
            self._sync_subscription(
                user_id=user_id,
                plan_id=plan_id,
                customer_id=provider_customer_id,
                subscription_id=provider_subscription_id,
                status=str(status or "active"),
                trial_end=_field(obj, "trial_end"),
                period_end=_field(obj, "current_period_end"),
                cancel_at_period_end=bool(_field(obj, "cancel_at_period_end", False)),
            )

    def _sync_subscription(
        self,
        *,
        user_id: str,
        plan_id: str,
        customer_id: str | None,
        subscription_id: str,
        status: str,
        trial_end: object,
        period_end: object,
        cancel_at_period_end: bool,
    ) -> None:
        payload = {
            "user_id": user_id,
            "plan_id": plan_id,
            "provider": "stripe",
            "provider_customer_id": customer_id,
            "provider_subscription_id": subscription_id,
            "status": status if status in {"active", "trialing", "past_due", "canceled", "expired"} else "active",
            "trial_ends_at": _epoch_to_iso(trial_end),
            "current_period_end": _epoch_to_iso(period_end),
            "cancel_at_period_end": cancel_at_period_end,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = requests.post(
            f"{self.supabase_url}/rest/v1/subscriptions?on_conflict=provider_subscription_id",
            headers=self._supabase_headers("resolution=merge-duplicates"),
            json=payload,
            timeout=15,
        )
        if not response.ok:
            raise BillingProviderError(f"Subscription synchronization failed ({response.status_code}).")

    def _client(self) -> Any:
        if not self.secret_key:
            raise BillingConfigurationError("STRIPE_SECRET_KEY is required.")
        try:
            from stripe import StripeClient
        except ImportError as exc:
            raise BillingConfigurationError("Install the Stripe Python SDK to enable billing.") from exc
        return StripeClient(self.secret_key, stripe_version=STRIPE_API_VERSION)

    def _supabase_headers(self, preference: str) -> dict[str, str]:
        return {
            "apikey": self.supabase_service_role_key,
            "Authorization": f"Bearer {self.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": f"return=minimal,{preference}",
        }


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _epoch_to_iso(value: object) -> str | None:
    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp > 0 else None
    except (TypeError, ValueError, OSError):
        return None


def _subscription_status_for_event(event_type: str) -> str:
    if event_type.endswith(".deleted"):
        return "canceled"
    if event_type == "checkout.session.completed":
        return "active"
    return "active"
