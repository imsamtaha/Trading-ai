from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.billing.stripe_checkout import (
    BillingConfigurationError,
    BillingProviderError,
    StripeBilling,
)

LOG = logging.getLogger("atlas.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


def _app_url(request: Request) -> str:
    return os.getenv("ATLAS_APP_URL", "").strip().rstrip("/") or str(request.base_url).rstrip("/")


@router.post("/checkout/{plan_id}")
def checkout(plan_id: str, request: Request) -> dict[str, str]:
    try:
        session = StripeBilling(app_url=_app_url(request)).create_checkout_session(plan_id)
        return {"checkout_url": session["url"], "plan": session["plan_id"]}
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BillingProviderError as exc:
        LOG.exception("Stripe Checkout failed.")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    try:
        billing = StripeBilling()
        event = billing.construct_event(
            await request.body(),
            request.headers.get("stripe-signature", ""),
        )
        billing.record_verified_event(event)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BillingProviderError as exc:
        LOG.warning("Rejected Stripe webhook: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}


@router.get("/success", response_class=HTMLResponse)
def success() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang="en"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>ATLAS subscription received</title>
        <body style="margin:0;background:#07090e;color:#f3f5f7;font:16px system-ui;padding:48px">
        <main style="max-width:620px;margin:auto"><p style="color:#ff8a24;font-weight:800">ATLAS THE ULTIMATE</p>
        <h1>Subscription received.</h1>
        <p>Access activates after the signed Stripe event is recorded. ATLAS remains read-only for subscribers.</p>
        <p><a style="color:#ff8a24" href="/dashboard">Open dashboard</a></p>
        </main></body></html>"""
    )
