from __future__ import annotations

import os
from typing import Any

import requests


class SupabaseBillingError(RuntimeError):
    pass


class SupabaseBillingJournal:
    """Private, idempotent billing event persistence for Stripe webhooks."""

    def __init__(self) -> None:
        self.base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.base_url or not self.service_role_key:
            raise SupabaseBillingError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for billing persistence."
            )

    def record_event(
        self,
        *,
        stripe_event_id: str,
        event_type: str,
        plan: str | None,
        customer_id: str | None,
        subscription_id: str | None,
        customer_email: str | None,
        subscription_status: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = requests.post(
            self.base_url + "/rest/v1/atlas_billing_events?on_conflict=stripe_event_id",
            headers={
                "apikey": self.service_role_key,
                "Authorization": "Bearer " + self.service_role_key,
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            json={
                "stripe_event_id": stripe_event_id,
                "event_type": event_type,
                "plan": plan,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "customer_email": customer_email,
                "subscription_status": subscription_status,
                "payload": payload,
            },
            timeout=12,
        )
        if not response.ok:
            raise SupabaseBillingError(
                "Supabase billing insert failed (" + str(response.status_code) + "): "
                + response.text[:500]
            )
        rows = response.json()
        return rows[0] if isinstance(rows, list) and rows else {}
