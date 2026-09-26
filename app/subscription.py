import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse

from app.billing.plans import PLANS

router = APIRouter(tags=["subscription"])


class AccessRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    plan: str = "free"


class MT5AccessRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    account_number: str = Field(min_length=3, max_length=40)
    server: str = Field(min_length=3, max_length=120)
    broker: str = "FxPro"


@router.get("/subscribe", response_class=HTMLResponse)
def subscribe() -> HTMLResponse:
    return HTMLResponse(SUBSCRIPTION_HTML)


@router.post("/subscription/request")
def request_access(payload: AccessRequest) -> dict:
    plan = payload.plan.lower().strip()
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="Choose signals or execution.")

    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    record = {
        "created_at": datetime.now(UTC).isoformat(),
        "name": payload.name.strip()[:120],
        "email": email,
        "plan": plan,
        "amount_usd": PLANS[plan].monthly_price,
        "status": "PENDING_REVIEW",
        "payment_required_now": True,
        "access_granted": False,
    }

    if not record["name"]:
        raise HTTPException(status_code=400, detail="Name is required.")

    requests_file = Path(
        os.getenv(
            "ATLAS_SUBSCRIPTION_REQUESTS_FILE",
            str(Path(__file__).resolve().parent.parent / "data" / "subscription_requests.jsonl"),
        )
    )
    requests_file.parent.mkdir(parents=True, exist_ok=True)
    with requests_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "status": "PENDING_REVIEW",
        "message": "Subscription request received. Pay with Whish Money and wait for manual approval.",
        "whish_url": f"/billing/whish/{plan}",
    }


@router.post("/subscription/mt5-request")
def request_mt5_access(payload: MT5AccessRequest) -> dict:
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    account_number = re.sub(r"[^0-9A-Za-z_-]", "", payload.account_number.strip())
    if not account_number:
        raise HTTPException(status_code=400, detail="MT5 account number is required.")

    record = {
        "created_at": datetime.now(UTC).isoformat(),
        "name": payload.name.strip()[:120],
        "email": email,
        "broker": payload.broker.strip()[:80] or "FxPro",
        "account_number": account_number[:40],
        "server": payload.server.strip()[:120],
        "status": "PENDING_READ_ONLY_CONNECTION",
        "password_collected": False,
        "live_trading_enabled": False,
        "note": "Trader must provide investor/read-only password through a secure private channel only.",
    }

    if not record["name"]:
        raise HTTPException(status_code=400, detail="Name is required.")
    if not record["server"]:
        raise HTTPException(status_code=400, detail="MT5 server name is required.")

    requests_file = Path(
        os.getenv(
            "ATLAS_MT5_ACCESS_REQUESTS_FILE",
            str(Path(__file__).resolve().parent.parent / "data" / "mt5_access_requests.jsonl"),
        )
    )
    requests_file.parent.mkdir(parents=True, exist_ok=True)
    with requests_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "status": "PENDING_READ_ONLY_CONNECTION",
        "message": "FxPro / MT5 entrance request received. Do not send the trading password here.",
        "dashboard": "/dashboard",
    }


SUBSCRIPTION_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS Access Request</title>
<style>
body{margin:0;background:#07090e;color:#f3f5f7;font:15px system-ui}
main{max-width:920px;margin:auto;padding:42px 20px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:22px 0}
.card,.form,.hero{background:#101620;border:1px solid #263246;border-radius:16px;padding:24px}
.price{font-size:38px;font-weight:900}
.muted{color:#a9b4c2}
button,.btn{background:#ff8a24;color:#101620;border:0;padding:13px 16px;border-radius:10px;font-weight:900;text-decoration:none;display:inline-block;text-align:center;cursor:pointer}
.btn.big{display:block;font-size:22px;padding:18px 20px;margin-top:16px}
button{width:100%;margin-top:10px}
input,select{width:100%;box-sizing:border-box;margin:8px 0 14px;padding:12px;border-radius:10px;border:1px solid #334155;background:#0b111a;color:#fff}
a{color:#ff8a24}
#result,#mt5-result{margin-top:12px;min-height:24px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style>
<body><main><p style="color:#ff8a24;font-weight:900">ATLAS THE ULTIMATE</p><h1>Choose your Whish subscription</h1>
<p>ATLAS now has two manual Whish subscription methods. The $99 plan sends signals. The $149 plan executes approved signals after account approval and safety-gate setup.</p>
<section class="hero"><h2>Whish payment only</h2><p class="muted">Payment requests are reviewed manually. A request or receipt does not activate access until the owner approves it.</p>
<a class="btn big" href="/billing/whish/signals">PAY $99 WITH WHISH - SIGNALS</a>
<a class="btn big" href="/billing/whish/execution">PAY $149 WITH WHISH - EXECUTION</a></section>
<div class="grid"><section class="card"><h2>ATLAS Signals</h2><div class="price">$99<small>/month</small></div><p class="muted">ATLAS sends trade signals with market context, risk notes, and dashboard access. You decide whether to place each trade.</p><a class="btn" href="/billing/whish/signals">Request $99 Whish payment</a></section>
<section class="card"><h2>ATLAS Execution</h2><div class="price">$149<small>/month</small></div><p class="muted">ATLAS executes approved signals after MT5/account approval, safety-gate setup, and manual activation by the owner.</p><a class="btn" href="/billing/whish/execution">Request $149 Whish payment</a></section></div>
<section class="form"><h2>Subscription request</h2><p class="muted">Choose one of the two Whish subscription methods. No Stripe prices are used here.</p>
<form id="access-form">
<label>Name</label><input name="name" autocomplete="name" required placeholder="Trader name">
<label>Email</label><input name="email" type="email" autocomplete="email" required placeholder="trader@example.com">
<label>Subscription</label><select name="plan"><option value="signals">ATLAS Signals - $99/month - sends signals</option><option value="execution">ATLAS Execution - $149/month - executes approved signals</option></select>
<button type="submit">Create subscription request</button></form><div id="result" role="status" aria-live="polite"></div>
<p class="muted">Do not send your main FxPro trading password on this page. Execution setup must use the approved private onboarding path.</p></section>
<section class="form" id="fxpro-mt5"><h2>FxPro / MT5 entrance</h2>
<p class="muted">Use this if you want ATLAS to prepare a read-only MT5 connection for your FxPro account.</p>
<form id="mt5-form">
<label>Name</label><input name="name" autocomplete="name" required placeholder="Trader name">
<label>Email</label><input name="email" type="email" autocomplete="email" required placeholder="trader@example.com">
<label>Broker</label><select name="broker"><option value="FxPro">FxPro</option><option value="MetaTrader 5">MetaTrader 5</option></select>
<label>MT5 account number</label><input name="account_number" required placeholder="Example: 592031391">
<label>MT5 server name</label><input name="server" required placeholder="Example: FxPro-MT5 Demo">
<button type="submit">Request FxPro / MT5 entrance</button></form>
<div id="mt5-result" role="status" aria-live="polite"></div>
<p class="muted"><strong>Security:</strong> do not enter your main trading password on this page. ATLAS will request investor/read-only access privately if needed.</p></section>
</main>
<script>
document.getElementById('access-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const result = document.getElementById('result');
  result.textContent = 'Sending request...';
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch('/subscription/request', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed.');
    result.innerHTML = data.message + ' <br><br><a class="btn" href="' + data.whish_url + '">Continue to Whish payment request</a>';
    form.reset();
  } catch (error) {
    result.textContent = error.message || 'Could not send request. Please try again.';
  }
});
document.getElementById('mt5-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const result = document.getElementById('mt5-result');
  result.textContent = 'Sending FxPro / MT5 request...';
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch('/subscription/mt5-request', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'MT5 request failed.');
    result.innerHTML = data.message + ' <br><br><a class="btn" href="' + data.dashboard + '">ENTER ATLAS DASHBOARD FREE</a>';
    form.reset();
  } catch (error) {
    result.textContent = error.message || 'Could not send MT5 request. Please try again.';
  }
});
</script><script src="/ui/preferences.js"></script></body></html>"""
