"""Manual Whish payment requests. These records NEVER grant subscription access."""
import os
import re
import secrets
import sqlite3
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from app.auth.supabase_auth import require_user
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.billing.plans import PLANS

router = APIRouter(prefix="/billing/whish", tags=["billing"])

LEGACY_PLAN_ALIASES = {"signals": "starter", "execution": "pro"}
ADMIN_EMAIL = "imsamtaha.ai@gmail.com"


def _database_path() -> Path:
    return Path(os.getenv("ATLAS_WHISH_DB", "data/whish_requests.sqlite3"))


def _ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS whish_requests (
        reference TEXT PRIMARY KEY, email TEXT NOT NULL, plan_id TEXT NOT NULL,
        amount_usd INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
        created_at TEXT NOT NULL, user_id TEXT)""")
    if "user_id" not in {row[1] for row in db.execute("PRAGMA table_info(whish_requests)") }:
        db.execute("ALTER TABLE whish_requests ADD COLUMN user_id TEXT")


def settings():
    recipient = os.getenv("ATLAS_WHISH_RECIPIENT", "").strip()
    contact = os.getenv("ATLAS_WHISH_SUPPORT", "").strip()
    phone = os.getenv("ATLAS_WHISH_PHONE", contact).strip()
    qr_image_url = os.getenv("ATLAS_WHISH_QR_IMAGE_URL", "").strip()
    enabled = os.getenv("ATLAS_WHISH_ENABLED", "false").lower() == "true"
    return {"available": enabled and bool(recipient and contact),
            "recipient": recipient, "support": contact,
            "phone": phone, "qr_image_url": qr_image_url}


class PaymentRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


@router.post("/{plan_id}/request")
def request_payment(plan_id: str, body: PaymentRequest, request: Request):
    user = require_user(request)
    if not user.email or body.email.strip().lower() != user.email.strip().lower():
        raise HTTPException(403, "Payment request email must match the signed-in account.")
    canonical_plan_id = LEGACY_PLAN_ALIASES.get(plan_id, plan_id)
    if canonical_plan_id not in PLANS or canonical_plan_id == "free":
        raise HTTPException(404, "Unknown subscription plan.")
    config = settings()
    if not config["available"]:
        raise HTTPException(503, "Whish Money is not configured yet.")
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Enter a valid email address.")
    plan = PLANS[canonical_plan_id]
    reference = "ATLAS-" + secrets.token_hex(12).upper()
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(path, timeout=5) as db:
            _ensure_schema(db)
            existing = db.execute(
                "SELECT reference FROM whish_requests WHERE email=? AND user_id=? AND plan_id=? AND status='PENDING_REVIEW'",
                (email, user.user_id, canonical_plan_id)).fetchone()
            if existing:
                reference = existing[0]
            else:
                db.execute("INSERT INTO whish_requests (reference, email, plan_id, amount_usd, status, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (reference, email, canonical_plan_id, plan.monthly_price, "PENDING_REVIEW",
                     datetime.now(timezone.utc).isoformat(), user.user_id))
    except sqlite3.Error as exc:
        raise HTTPException(503, "Payment request storage unavailable.") from exc
    notification_sent = _notify_admin(reference, email, canonical_plan_id) if not existing else False
    return {"reference": reference, "status": "PENDING_REVIEW",
            "admin_notification_sent": notification_sent,
            "amount_usd": plan.monthly_price, "trial_days": plan.trial_days,
            "recipient": config["recipient"], "support": config["support"],
            "phone": config["phone"], "qr_image_url": config["qr_image_url"],
            "access_granted": False, "automatic_renewal": False}


@router.get("/{plan_id}", response_class=HTMLResponse)
def payment_page(plan_id: str):
    canonical_plan_id = LEGACY_PLAN_ALIASES.get(plan_id, plan_id)
    if canonical_plan_id not in PLANS or canonical_plan_id == "free":
        raise HTTPException(404, "Unknown subscription plan.")
    plan = PLANS[canonical_plan_id]
    feature_items = "".join(f"<li>{feature}</li>" for feature in plan.features)
    config = settings()
    phone = escape(config["phone"])
    support = escape(config["support"])
    qr_image_url = escape(config["qr_image_url"])
    phone_html = (
        f"<p><strong>Send Whish payment to:</strong> {phone}</p>"
        if phone
        else "<p>Payment phone number is not configured yet.</p>"
    )
    qr_html = (
        f'<p><img class="qr" src="{qr_image_url}" alt="Whish payment QR code"></p>'
        if qr_image_url
        else "<p>QR code is not configured yet. Use the phone number or contact support.</p>"
    )
    html = (
        WHISH_HTML.replace("__PLAN__", plan_id)
        .replace("__PLAN_NAME__", escape(plan.name))
        .replace("__PLAN_PRICE__", str(plan.monthly_price))
        .replace("__PLAN_FEATURES__", feature_items)
        .replace("__WHISH_PHONE_BLOCK__", phone_html)
        .replace("__WHISH_QR_BLOCK__", qr_html)
        .replace("__WHISH_SUPPORT__", support)
    )
    return HTMLResponse(html)


WHISH_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS | Whish Money</title>
<style>body{background:#07090e;color:#f3f5f7;font:16px system-ui;margin:0}
main{max-width:600px;margin:40px auto;padding:24px}input,button{font:inherit;padding:12px;border-radius:8px}
input{box-sizing:border-box;width:100%;margin:12px 0}button{background:#ff8a24;color:#111;border:0}
a{color:#ff8a24}dt{margin-top:12px}dd{margin:4px 0;overflow-wrap:anywhere}.paybox{border:1px solid #263246;background:#101620;border-radius:14px;padding:16px;margin:18px 0}.qr{max-width:220px;width:100%;border-radius:12px;background:#fff;padding:8px}</style>
<body><main><h1>Whish Money</h1><p>Manual payment review</p>
<h2>__PLAN_NAME__ - $__PLAN_PRICE__/month</h2>
<ul>__PLAN_FEATURES__</ul>
<p>ATLAS paid plans add private analytics and demo-only simulation. No plan submits real-money broker orders.</p>
<section class="paybox"><h2>Send payment</h2>
__WHISH_PHONE_BLOCK__
__WHISH_QR_BLOCK__
<p>Support / confirmation: __WHISH_SUPPORT__</p></section>
<p>Contact support to confirm the start date and payment instructions. Monthly renewals are manual.</p>
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
 ['Recipient',d.recipient],['Whish phone',d.phone||d.support],['Support',d.support]]){let dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;list.append(dt,dd)}
 result.append(list);
 }catch(e){result.textContent=e.message}finally{button.disabled=false}
});
</script><script src="/ui/preferences.js"></script></body></html>"""



def _assert_admin(request: Request) -> None:
    user = require_user(request)
    if not user.email or user.email.strip().lower() != ADMIN_EMAIL:
        raise HTTPException(403, "Owner approval required.")


def _activate_subscription(user_id: str, plan_id: str, reference: str) -> None:
    import requests
    from app.auth.supabase_auth import current_access_token, supabase_publishable_key
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = supabase_publishable_key()
    if not base or not key:
        raise HTTPException(503, "Subscription approval is unavailable.")
    try:
        response = requests.post(
            f"{base}/rest/v1/rpc/atlas_approve_whish_subscription",
            headers={"apikey": key, "Authorization": f"Bearer {current_access_token()}", "Content-Type": "application/json"},
            json={"target_user_id": user_id, "selected_plan": plan_id, "payment_reference": reference}, timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(503, "Subscription approval is unavailable.") from exc
    if not response.ok:
        raise HTTPException(503, "Subscription approval was not recorded.")


@router.get("/admin/requests")
def admin_requests(request: Request):
    _assert_admin(request)
    try:
        with sqlite3.connect(_database_path(), timeout=5) as db:
            _ensure_schema(db)
            rows = db.execute("SELECT reference, email, plan_id, amount_usd, status, created_at FROM whish_requests WHERE status='PENDING_REVIEW' ORDER BY created_at").fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(503, "Payment request storage unavailable.") from exc
    return {"requests": [dict(zip(("reference", "email", "plan_id", "amount_usd", "status", "created_at"), row)) for row in rows]}



@router.post("/admin/{reference}/approve")
def approve_request(reference: str, request: Request):
    _assert_admin(request)
    if not re.fullmatch(r"ATLAS-[A-F0-9]{24}", reference):
        raise HTTPException(404, "Unknown payment reference.")
    try:
        with sqlite3.connect(_database_path(), timeout=15) as db:
            db.execute("BEGIN IMMEDIATE")
            _ensure_schema(db)
            row = db.execute(
                "SELECT user_id, plan_id, status FROM whish_requests WHERE reference=?", (reference,)
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Unknown payment reference.")
            user_id, plan_id, status = row
            if status != "PENDING_REVIEW":
                raise HTTPException(409, "Payment request was already reviewed.")
            if not user_id or plan_id not in PLANS or plan_id == "free":
                raise HTTPException(409, "Payment request has no verified signed-in owner.")
            _activate_subscription(user_id, plan_id, reference)
            db.execute("UPDATE whish_requests SET status='APPROVED' WHERE reference=? AND status='PENDING_REVIEW'", (reference,))
    except sqlite3.Error as exc:
        raise HTTPException(503, "Payment request storage unavailable.") from exc
    return {"reference": reference, "status": "APPROVED", "access_granted": True}



def _notify_admin(reference: str, buyer_email: str, plan_id: str) -> bool:
    host = os.getenv("ATLAS_SMTP_HOST", "").strip()
    sender = os.getenv("ATLAS_SMTP_FROM", "").strip()
    username = os.getenv("ATLAS_SMTP_USER", "").strip()
    password = os.getenv("ATLAS_SMTP_PASSWORD", "").strip()
    if not (host and sender and username and password):
        return False
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ADMIN_EMAIL
    message["Subject"] = f"ATLAS Whish review {reference}"
    message.set_content(
        f"Payment request: {reference}\nAccount: {buyer_email}\nPlan: {plan_id}\n"
        "Verify the Whish transfer independently before approving.\n"
        "Review: https://justai-atlas.online/admin/whish\n"
    )
    try:
        with smtplib.SMTP(host, int(os.getenv("ATLAS_SMTP_PORT", "587")), timeout=10) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError):
        return False
