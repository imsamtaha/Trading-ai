from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["subscription"])


@router.get("/subscribe", response_class=HTMLResponse)
def subscribe() -> HTMLResponse:
    html = SUBSCRIPTION_HTML
    for plan_id in ("reader", "pro"):
        button = f'<button onclick="checkout(\'{plan_id}\',this)">Start free trial</button>'
        html = html.replace(button, button +
            f'<p><a href="/billing/whish/{plan_id}">Pay with Whish Money</a></p>')
    html = html.replace("</main>", '<p>Whish requests are reviewed manually. Automatic renewal is not available.</p></main>')
    return HTMLResponse(html.replace("</body>",
        '<script src="/ui/preferences.js"></script></body>'))


SUBSCRIPTION_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS Reader Access</title>
<style>
:root{--bg:#07090e;--card:#101620;--line:#263246;--text:#f3f5f7;--muted:#919bad;--orange:#ff8a24;--green:#3bd68d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#182437,#07090e 42%);color:var(--text);font:15px Inter,system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:48px 20px}.brand,.eyebrow{font-weight:900;letter-spacing:.08em;color:var(--orange)}h1{font-size:clamp(34px,6vw,56px);line-height:1.03;margin:14px 0}p{color:var(--muted);line-height:1.65}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:28px}.card{background:linear-gradient(180deg,#111925,#0d131d);border:1px solid var(--line);border-radius:20px;padding:26px}.featured{border-color:var(--orange);box-shadow:0 14px 45px #0008}.price{font-size:42px;font-weight:900;margin-top:10px}.price small{font-size:14px;color:var(--muted)}.trial{color:var(--green);font-weight:800}ul{padding-left:19px;line-height:1.9;color:#c9d0da;min-height:130px}button{border:0;background:var(--orange);color:#090b0f;padding:13px 18px;border-radius:12px;font-weight:900;font-size:15px;width:100%;cursor:pointer}button:disabled{opacity:.65;cursor:wait}.notice{margin-top:24px;border-left:3px solid var(--orange);padding:12px 14px;background:#ff8a240b;border-radius:8px}@media(max-width:720px){.grid{grid-template-columns:1fr}main{padding:30px 16px}}
</style></head><body><main><div class="brand">ATLAS THE ULTIMATE</div><h1>Read the market. Keep control.</h1>
<p>Reader plans provide observational access to ATLAS telemetry and market context. They do not provide account control, personal investment advice, or any promise of returns.</p>
<div class="grid">
<section class="card"><div class="eyebrow">ATLAS READER</div><div class="price">$49<small>/month</small></div><p class="trial">3-day free trial</p><ul><li>Live read-only MT5 telemetry</li><li>Wall Street and financial-news board</li><li>Open positions and floating P/L</li></ul><button onclick="checkout('reader',this)">Start free trial</button></section>
<section class="card featured"><div class="eyebrow">ATLAS PRO READER</div><div class="price">$99<small>/month</small></div><p class="trial">3-day free trial</p><ul><li>Everything in Reader</li><li>Expanded multi-asset opportunity matrix</li><li>Priority subscriber briefings</li></ul><button onclick="checkout('pro',this)">Start free trial</button></section>
</div><p class="notice">Payments use Stripe-hosted Checkout. The dashboard is read-only and cannot place or change an MT5 trade.</p>
</main><script>
async function checkout(plan,button){button.disabled=true;var label=button.textContent;button.textContent="Opening secure checkout...";try{var response=await fetch("/billing/checkout/"+plan,{method:"POST"});var data=await response.json();if(!response.ok){throw Error(data.detail||"Checkout unavailable.")}window.location.assign(data.checkout_url)}catch(error){button.disabled=false;button.textContent=label;alert(error.message)}}
</script></body></html>'''
