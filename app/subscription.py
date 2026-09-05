from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.billing.stripe_checkout import (
    BillingConfigurationError,
    BillingProviderError,
    StripeBilling,
    public_plans,
)

router = APIRouter(tags=["subscription"])


@router.get("/billing/plans")
def billing_plans() -> dict:
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


@router.post("/billing/checkout/{plan_id}")
def create_checkout(plan_id: str) -> dict[str, str]:
    try:
        return StripeBilling().create_checkout_session(plan_id)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/billing/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    billing = StripeBilling()
    try:
        event = billing.construct_event(payload, signature)
        billing.record_verified_event(event)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BillingProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}


@router.get("/subscribe", response_class=HTMLResponse)
def subscribe(request: Request) -> HTMLResponse:
    billing = StripeBilling()
    checkout_state = request.query_params.get("checkout")
    cards = "".join(_plan_card(plan, billing.checkout_configured(plan.id)) for plan in public_plans())
    notice = ""
    if checkout_state == "success":
        notice = "<div class='notice success'>Checkout completed. Your access is activated after the verified payment webhook is processed.</div>"
    elif checkout_state == "cancelled":
        notice = "<div class='notice'>Checkout was cancelled. No subscription was created.</div>"

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS — Plans</title>
<style>
:root{{--bg:#07090e;--card:#101620;--line:#263246;--text:#f3f5f7;--muted:#919bad;--orange:#ff8a24;--green:#3bd68d}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 20% 0,#182437,#07090e 42%);color:var(--text);font:15px Inter,system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:48px 20px}}.brand{{font-weight:900;letter-spacing:.08em;color:var(--orange)}}h1{{font-size:44px;line-height:1.05;margin:14px 0}}p{{color:var(--muted);line-height:1.65}}.plans{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:28px}}.card{{background:linear-gradient(180deg,#111925,#0d131d);border:1px solid var(--line);border-radius:18px;padding:24px}}.card.featured{{border-color:var(--orange);box-shadow:0 14px 45px #ff8a2412}}.price{{font-size:38px;font-weight:900}}.trial{{color:var(--green);font-weight:800}}ul{{padding-left:19px;line-height:1.9;color:#c9d0da;min-height:150px}}button{{margin-top:16px;background:var(--orange);color:#090b0f;border:0;padding:13px 18px;border-radius:12px;font-weight:900;cursor:pointer;width:100%}}button:disabled{{opacity:.55;cursor:not-allowed}}.mini{{font-size:12px;color:var(--muted)}}.notice{{margin:18px 0;padding:12px;border-left:3px solid var(--orange);background:#ff8a2410;border-radius:8px}}.notice.success{{border-color:var(--green)}}#message{{margin-top:16px;color:var(--muted)}}@media(max-width:760px){{.plans{{grid-template-columns:1fr}}h1{{font-size:34px}}}}</style></head>
<body><main><div class="brand">ATLAS THE ULTIMATE</div><h1>Choose your ATLAS access.</h1>
<p>Every plan starts with three days free. ATLAS provides market intelligence and risk-aware automation tools; it does not guarantee investment results. Live execution is independently protected by the MT5 risk gate.</p>
{notice}<section class="plans">{cards}</section><div id="message" role="status"></div>
<p class="mini">Checkout is hosted by the payment provider. We do not collect card details in ATLAS. Tax is not automatically enabled until the business has the required tax registrations.</p>
<script>
const message=document.getElementById('message');
document.querySelectorAll('[data-plan]').forEach(button=>button.addEventListener('click',async()=>{{const plan=button.dataset.plan;button.disabled=true;message.textContent='Opening secure checkout…';try{{const response=await fetch('/billing/checkout/'+encodeURIComponent(plan),{{method:'POST'}});const payload=await response.json();if(!response.ok)throw Error(payload.detail||'Checkout is unavailable.');window.location.assign(payload.url)}}catch(error){{message.textContent=error.message;button.disabled=false}}}}));
</script></main></body></html>"""
    return HTMLResponse(page)


def _plan_card(plan, configured: bool) -> str:
    features = "".join(f"<li>{html.escape(feature)}</li>" for feature in plan.features)
    label = "Start 3-day free trial" if configured else "Payment setup pending"
    disabled = "" if configured else " disabled"
    featured = " featured" if plan.id == "trader" else ""
    return f"""<article class="card{featured}">
<div class="mini">{html.escape(plan.name.upper())}</div>
<div class="price">${plan.monthly_price}<span class="mini"> / month</span></div>
<p class="trial">{plan.trial_days} days free, then ${plan.monthly_price}/month.</p>
<ul>{features}</ul>
<button data-plan="{html.escape(plan.id)}"{disabled}>{label}</button>
</article>"""
