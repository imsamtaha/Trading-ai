"""Manual Whish payment requests. These records NEVER grant subscription access."""
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
    enabled = os.getenv("ATLAS_WHISH_ENABLED", "false").lower() == "true"
    return {"available": enabled and bool(recipient and contact),
            "recipient": recipient, "support": contact}


class PaymentRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


@router.post("/{plan_id}/request")
def request_payment(plan_id: str, body: PaymentRequest):
    if plan_id not in PLANS:
        raise HTTPException(404, "Unknown subscription plan.")
    config = settings()
    if not config["available"]:
        raise HTTPException(503, "Whish Money is not configured yet.")
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
    return {"reference": reference, "status": "PENDING_REVIEW",
            "amount_usd": plan.monthly_price, "trial_days": plan.trial_days,
            "recipient": config["recipient"], "support": config["support"],
            "access_granted": False, "automatic_renewal": False}


@router.get("/{plan_id}", response_class=HTMLResponse)
def payment_page(plan_id: str):
    if plan_id not in PLANS:
        raise HTTPException(404, "Unknown subscription plan.")
    return HTMLResponse(WHISH_HTML.replace("__PLAN__", plan_id))


WHISH_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS | Whish Money</title>
<style>body{background:#07090e;color:#f3f5f7;font:16px system-ui;margin:0}
main{max-width:600px;margin:40px auto;padding:24px}input,button{font:inherit;padding:12px;border-radius:8px}
input{box-sizing:border-box;width:100%;margin:12px 0}button{background:#ff8a24;color:#111;border:0}
a{color:#ff8a24}dt{margin-top:12px}dd{margin:4px 0;overflow-wrap:anywhere}</style>
<body><main><h1>Whish Money</h1><p>Manual payment review</p>
<p>Request your 3-day trial first. Contact support to confirm the start date and payment instructions. Monthly renewals are manual.</p>
<p>A request or receipt does not activate access. Payment must be verified by the owner.</p>
<form id="requestForm"><label for="email">Email address</label><input id="email" type="email" maxlength="254" required autocomplete="email">
<button id="submit">Request Whish payment</button></form>
<div id="result" role="status" aria-live="polite"></div><p><a href="/subscribe">Back to plans</a></p></main>
<script>
document.getElementById('requestForm').addEventListener('submit',async e=>{
 e.preventDefault();const button=document.getElementById('submit'),result=document.getElementById('result');
 button.disabled=true;result.replaceChildren();
 try{const r=await fetch('/billing/whish/__PLAN__/request',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({email:document.getElementById('email').value})});const d=await r.json();
 if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Payment request unavailable.');
 const list=document.createElement('dl');
 for(const [label,value] of [['Reference',d.reference],['Status','Pending review'],['Monthly price',d.amount_usd+' USD'],
 ['Recipient',d.recipient],['Support',d.support]]){let dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;list.append(dt,dd)}
 result.append(list);
 }catch(e){result.textContent=e.message}finally{button.disabled=false}
});
</script><script src="/ui/preferences.js"></script></body></html>"""
