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

SUBSCRIPTION_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS Reader Access</title>
<style>body{margin:0;background:#07090e;color:#f3f5f7;font:15px system-ui}main{max-width:900px;margin:auto;padding:48px 20px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}.card{background:#101620;border:1px solid #263246;border-radius:16px;padding:24px}.price{font-size:42px;font-weight:900}button{background:#ff8a24;border:0;padding:12px;border-radius:10px;font-weight:800;width:100%}a{color:#ff8a24}@media(max-width:720px){.grid{grid-template-columns:1fr}}</style>
<body><main><p style="color:#ff8a24;font-weight:900">ATLAS THE ULTIMATE</p><h1>Read the market. Keep control.</h1>
<p>Read-only ATLAS telemetry and market context. Payment requests are reviewed manually through Whish Money.</p>
<div class="grid"><section class="card"><h2>ATLAS Reader</h2><div class="price">$49<small>/month</small></div><p>3-day free trial</p><a href="/billing/whish/reader">Pay with Whish Money</a></section>
<section class="card"><h2>ATLAS Pro Reader</h2><div class="price">$99<small>/month</small></div><p>3-day free trial</p><a href="/billing/whish/pro">Pay with Whish Money</a></section></div>
<p>Manual review only; no automatic renewal or automatic access activation.</p></main><script src="/ui/preferences.js"></script></body></html>"""
