from __future__ import annotations

import html
import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["subscription"])


@router.get("/subscribe", response_class=HTMLResponse)
def subscribe() -> HTMLResponse:
    checkout_url = os.getenv("ATLAS_CHECKOUT_URL", "").strip()
    contact_url = os.getenv("ATLAS_CONTACT_URL", "").strip()
    price = os.getenv("ATLAS_SUBSCRIPTION_PRICE", "$19/month").strip()
    trial = os.getenv("ATLAS_SUBSCRIPTION_TRIAL", "7-day viewer trial").strip()
    cta_url = checkout_url or contact_url or "/dashboard"
    cta_label = "Subscribe now" if checkout_url else "Request subscriber access"

    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS — Subscriber Access</title>
<style>
:root{{--bg:#07090e;--card:#101620;--line:#263246;--text:#f3f5f7;--muted:#919bad;--orange:#ff8a24;--green:#3bd68d}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 20% 0,#182437,#07090e 42%);color:var(--text);font:15px Inter,system-ui,sans-serif}}main{{max-width:980px;margin:auto;padding:48px 20px}}.brand{{font-weight:900;letter-spacing:.08em;color:var(--orange)}}h1{{font-size:44px;line-height:1.05;margin:14px 0}}p{{color:var(--muted);line-height:1.65}}.grid{{display:grid;grid-template-columns:1.4fr .8fr;gap:16px;margin-top:28px}}.card{{background:linear-gradient(180deg,#111925,#0d131d);border:1px solid var(--line);border-radius:18px;padding:24px}}.price{{font-size:36px;font-weight:900}}ul{{padding-left:19px;line-height:1.9;color:#c9d0da}}a.btn{{display:inline-block;margin-top:16px;background:var(--orange);color:#090b0f;text-decoration:none;padding:13px 18px;border-radius:12px;font-weight:900}}.ok{{color:var(--green)}}.mini{{font-size:12px;color:var(--muted)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}h1{{font-size:34px}}}}</style></head>
<body><main><div class="brand">ATLAS THE ULTIMATE</div><h1>Watch ATLAS trade intelligence in real time.</h1><p>Subscriber access is read-only. Members can follow the verified MT5 account telemetry, open positions, floating P/L, ranked market opportunities, ATLAS confidence, and multi-timeframe market state. Subscription access does not provide control of the trading account or guarantee trading results.</p>
<div class="grid"><section class="card"><div class="mini">SUBSCRIBER OBSERVATORY</div><div class="price">{html.escape(price)}</div><p>{html.escape(trial)}</p><ul><li>Live read-only MT5 account telemetry</li><li>Open-position and floating P/L visibility</li><li>Multi-asset opportunity matrix</li><li>5m / 15m / 30m / 1h market state</li><li>ATLAS signal score and confidence</li><li>Private subscriber login through Cloudflare Access</li></ul><a class="btn" href="{html.escape(cta_url, quote=True)}">{html.escape(cta_label)}</a></section>
<aside class="card"><div class="mini">HOW ACCESS WORKS</div><p><span class="ok">1.</span> Complete subscription or request access.</p><p><span class="ok">2.</span> Your email is added to the subscriber access list.</p><p><span class="ok">3.</span> Open the private dashboard link.</p><p><span class="ok">4.</span> Verify by email one-time code.</p><p><span class="ok">5.</span> Watch ATLAS telemetry live.</p><p class="mini">Past or live performance can change. This dashboard is informational and observational, not a promise of profit.</p></aside></div></main></body></html>'''
    return HTMLResponse(page)
