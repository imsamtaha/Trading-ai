"""Manual Whish Pay payment requests.

The manual fallback NEVER grants subscription access. Merchant checkout must remain
fail-closed until Whish provides approved merchant credentials and API contract.
"""
import html
import os
import re
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.billing.plans import PLANS

router = APIRouter(prefix="/billing/whish", tags=["billing"])


def settings():
    recipient = os.getenv("ATLAS_WHISH_RECIPIENT", "").strip()
    contact = os.getenv("ATLAS_WHISH_SUPPORT", "").strip()
    qr_image_url = os.getenv("ATLAS_WHISH_QR_IMAGE_URL", "").strip()
    enabled = os.getenv("ATLAS_WHISH_ENABLED", "false").lower() == "true"
    return {
        "available": enabled and bool(recipient and contact),
        "provider": "Whish Pay",
        "recipient": recipient,
        "support": contact,
        "qr_image_url": qr_image_url if qr_image_url.startswith("https://") else "",
        "mode": "manual_review" if enabled and bool(recipient and contact)
        else "merchant_activation_pending",
    }


class PaymentRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


@router.post("/{plan_id}/request")
def request_payment(plan_id: str, body: PaymentRequest):
    if plan_id not in PLANS:
        raise HTTPException(404, "Unknown subscription plan.")
    config = settings()
    if not config["available"]:
        raise HTTPException(503, "Whish Pay is not configured yet.")
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Enter a valid email address.")
    plan = PLANS[plan_id]
    reference = "ATLAS-" + secrets.token_hex(12).upper()
    path = Path(os.getenv("ATLAS_WHISH_DB", "data/whish_requests.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(path, timeout=5) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS whish_requests (
                reference TEXT PRIMARY KEY, email TEXT NOT NULL,
                plan_id TEXT NOT NULL, amount_usd INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_REVIEW', created_at TEXT NOT NULL)""")
            existing = db.execute(
                "SELECT reference FROM whish_requests WHERE email=? AND plan_id=? AND status='PENDING_REVIEW'",
                (email, plan_id)).fetchone()
            if existing:
                reference = existing[0]
            else:
                db.execute("INSERT INTO whish_requests VALUES (?, ?, ?, ?, ?, ?)",
                    (reference, email, plan_id, plan.monthly_price, "PENDING_REVIEW",
                     datetime.now(timezone.utc).isoformat()))
    except sqlite3.Error as exc:
        raise HTTPException(503, "Payment request storage unavailable.") from exc
    return {
        "provider": "Whish Pay",
        "reference": reference,
        "status": "PENDING_REVIEW",
        "amount_usd": plan.monthly_price,
        "trial_days": plan.trial_days,
        "recipient": config["recipient"],
        "support": config["support"],
        "access_granted": False,
        "automatic_renewal": False,
        "merchant_checkout_active": False,
    }


@router.get("/{plan_id}", response_class=HTMLResponse)
def payment_page(plan_id: str):
    if plan_id not in PLANS:
        raise HTTPException(404, "Unknown subscription plan.")
    plan = PLANS[plan_id]
    config = settings()

    recipient = config["recipient"] or "76420910"
    support = config["support"] or "info@justai-atlas.online"
    qr_url = config["qr_image_url"]
    qr_block = (
        f'<img class="qr-image" src="{html.escape(qr_url, quote=True)}" alt="Whish Money payment QR code">'
        if qr_url
        else '<div class="qr-placeholder" aria-label="QR code pending configuration"><span>W</span><small>QR READY WHEN CONFIGURED</small></div>'
    )
    availability_note = (
        "Whish Money is active for manual payment review."
        if config["available"]
        else "Whish Money checkout is shown in preview mode until merchant configuration is completed."
    )

    page = WHISH_HTML
    replacements = {
        "__PLAN__": plan_id,
        "__PLAN_NAME__": html.escape(plan.name),
        "__PRICE__": str(plan.monthly_price),
        "__RECIPIENT__": html.escape(recipient),
        "__SUPPORT__": html.escape(support),
        "__QR_BLOCK__": qr_block,
        "__AVAILABILITY_NOTE__": html.escape(availability_note),
        "__REQUEST_DISABLED__": "" if config["available"] else "disabled",
        "__REQUEST_LABEL__": "Request payment review" if config["available"] else "Activation pending",
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return HTMLResponse(page)


WHISH_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS | Whish Money</title>
<style>
:root{color-scheme:dark;--bg:#05070c;--panel:#0c111b;--panel2:#101722;--line:#202b39;--text:#f5f7fb;--muted:#8d98a9;--red:#f52245;--orange:#ff8a24;--blue:#6ea8ff}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 50% -10%,#141c29 0,#070a10 36%,var(--bg) 70%);color:var(--text);font:15px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
main{width:min(720px,calc(100% - 28px));margin:28px auto 60px}
.topline{display:flex;justify-content:space-between;gap:20px;align-items:flex-end;margin-bottom:18px}
.eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#758196}
h1{font-size:clamp(30px,6vw,48px);line-height:1.04;margin:6px 0 0;letter-spacing:-.04em}
.plan{color:var(--muted);font-size:13px;text-align:right}
.card{background:linear-gradient(180deg,rgba(17,24,36,.97),rgba(9,14,22,.98));border:1px solid var(--line);border-radius:22px;overflow:hidden;box-shadow:0 30px 80px #0008}
.card-head{display:flex;align-items:center;gap:12px;padding:18px 18px 16px;border-bottom:1px solid #1a2431}
.logo{width:42px;height:42px;border-radius:10px;background:linear-gradient(145deg,#ff2c50,#cb1031);display:grid;place-items:center;box-shadow:inset 0 0 0 1px #ff6980aa,0 8px 20px #f5224533;font-weight:900;font-size:21px}
.brand{font-size:21px;font-weight:760;letter-spacing:-.02em}
.badge{margin-left:auto;padding:6px 10px;border:1px solid #344153;border-radius:8px;color:#a6b0c0;font-size:10px;letter-spacing:.14em;font-weight:700}
.card-body{padding:24px}
.scan-title{text-align:center;color:#9ba6b7;font-size:11px;letter-spacing:.12em;font-weight:700;margin-bottom:16px}
.qr-wrap{display:grid;place-items:center;min-height:288px}
.qr-image,.qr-placeholder{width:min(270px,78vw);aspect-ratio:1;border-radius:14px;background:#fff;padding:12px;box-shadow:0 12px 35px #0007}
.qr-image{object-fit:contain}
.qr-placeholder{display:grid;place-items:center;color:#0c111b;background:repeating-conic-gradient(#0d1117 0 25%,#fff 0 50%) 0/24px 24px;position:relative;overflow:hidden}
.qr-placeholder:after{content:"";position:absolute;inset:28%;background:#fff;border-radius:12px}
.qr-placeholder span{z-index:1;font-size:64px;font-weight:950;color:var(--red)}
.qr-placeholder small{z-index:1;position:absolute;bottom:18px;background:#fff;color:#222;padding:4px 7px;border-radius:5px;font-size:8px;font-weight:800;letter-spacing:.05em}
.send-row{margin-top:22px;padding:16px;border:1px solid #1d2a38;border-radius:14px;background:#0a1018;display:grid;grid-template-columns:44px 1fr auto;align-items:center;gap:12px}
.phone-icon{width:40px;height:40px;border-radius:10px;background:#152337;display:grid;place-items:center;color:var(--blue);font-size:19px}
.send-label{font-size:10px;letter-spacing:.12em;color:#7f8a9b;font-weight:700}
.number{font-size:18px;font-weight:800;letter-spacing:.02em;margin-top:3px;overflow-wrap:anywhere}
.copy{border:1px solid #283648;background:#141d2a;color:#dce4ef;border-radius:9px;padding:10px 13px;font-weight:800;font-size:11px;cursor:pointer}
.copy:active{transform:translateY(1px)}
.notice{margin-top:16px;padding:13px 14px;border-radius:12px;background:#0c1420;border:1px solid #1b2a3a;color:#9aa6b7;font-size:12px}
.review{margin-top:18px;padding-top:18px;border-top:1px solid #1b2634}
.review h2{font-size:16px;margin:0 0 4px}
.review p{margin:0 0 12px;color:#8995a7;font-size:12px}
label{font-size:11px;color:#aeb8c7;font-weight:700}
input{width:100%;margin:7px 0 10px;padding:12px 13px;border:1px solid #263447;background:#0a1018;color:#fff;border-radius:10px;font:inherit;outline:none}
input:focus{border-color:#5b6f88}
.submit{width:100%;padding:12px 16px;border:0;border-radius:10px;background:linear-gradient(180deg,#ff9a38,#ff7a12);color:#16100a;font-weight:850;font:inherit;cursor:pointer}
.submit:disabled{opacity:.45;cursor:not-allowed}
#result{margin-top:14px}
dl{margin:0;padding:13px;border-radius:11px;background:#09111a;border:1px solid #1b2938}
dt{font-size:10px;color:#7f8b9d;text-transform:uppercase;letter-spacing:.1em;margin-top:10px}dt:first-child{margin-top:0}
dd{margin:2px 0;color:#eef3fa;overflow-wrap:anywhere}
.back{display:inline-block;margin-top:16px;color:#aab5c5;text-decoration:none}
@media(max-width:560px){.topline{align-items:flex-start;flex-direction:column}.plan{text-align:left}.card-body{padding:18px}.send-row{grid-template-columns:40px 1fr}.copy{grid-column:1/-1;width:100%}.qr-wrap{min-height:250px}}
</style>
</head>
<body>
<main>
  <div class="topline">
    <div><div class="eyebrow">ATLAS / JUST AI · PAYMENT METHOD</div><h1>Whish Money</h1></div>
    <div class="plan">__PLAN_NAME__ · <strong>$__PRICE__/month</strong></div>
  </div>

  <section class="card" aria-labelledby="whish-title">
    <div class="card-head">
      <div class="logo" aria-hidden="true">W</div>
      <div class="brand" id="whish-title">Whish Money</div>
      <div class="badge">LOCAL</div>
    </div>

    <div class="card-body">
      <div class="scan-title">SCAN QR CODE TO PAY</div>
      <div class="qr-wrap">__QR_BLOCK__</div>

      <div class="send-row">
        <div class="phone-icon" aria-hidden="true">☎</div>
        <div>
          <div class="send-label">OR SEND TO NUMBER</div>
          <div class="number" id="whishNumber">__RECIPIENT__</div>
        </div>
        <button class="copy" type="button" id="copyNumber">COPY</button>
      </div>

      <div class="notice">__AVAILABILITY_NOTE__ Payment verification is manual and subscription access remains locked until review is completed.</div>

      <div class="review">
        <h2>Payment review</h2>
        <p>After sending the payment, create a review reference. A request or receipt never activates access automatically.</p>
        <form id="requestForm">
          <label for="email">Email address</label>
          <input id="email" type="email" maxlength="254" required autocomplete="email" placeholder="you@example.com">
          <button class="submit" id="submit" __REQUEST_DISABLED__>__REQUEST_LABEL__</button>
        </form>
        <div id="result" role="status" aria-live="polite"></div>
      </div>

      <a class="back" href="/#plans">← Back to ATLAS plans</a>
    </div>
  </section>
</main>

<script>
const copyButton=document.getElementById('copyNumber');
copyButton.addEventListener('click',async()=>{
  const value=document.getElementById('whishNumber').textContent.trim();
  try{await navigator.clipboard.writeText(value);copyButton.textContent='COPIED';setTimeout(()=>copyButton.textContent='COPY',1400)}
  catch(_){copyButton.textContent='SELECT';}
});

document.getElementById('requestForm').addEventListener('submit',async e=>{
 e.preventDefault();
 const button=document.getElementById('submit'),result=document.getElementById('result');
 if(button.disabled)return;
 button.disabled=true;result.replaceChildren();
 try{
   const r=await fetch('/billing/whish/__PLAN__/request',{
     method:'POST',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({email:document.getElementById('email').value})
   });
   const d=await r.json();
   if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Payment request unavailable.');
   const list=document.createElement('dl');
   for(const [label,value] of [
     ['Provider',d.provider],['Reference',d.reference],['Status','Pending review'],
     ['Monthly price',d.amount_usd+' USD'],['Recipient',d.recipient],['Support',d.support]
   ]){
     let dt=document.createElement('dt'),dd=document.createElement('dd');
     dt.textContent=label;dd.textContent=value;list.append(dt,dd)
   }
   result.append(list);
 }catch(e){result.textContent=e.message}
 finally{button.disabled=false}
});
</script>
<script src="/ui/preferences.js"></script>
</body>
</html>"""
