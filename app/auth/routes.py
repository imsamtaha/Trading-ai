from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth.supabase_auth import require_user, verify_access_token

router = APIRouter(tags=["auth"])


class SessionPayload(BaseModel):
    access_token: str


def _public_auth_config() -> dict[str, str]:
    return {
        "url": os.getenv("SUPABASE_URL", "").strip(),
        "anon_key": os.getenv("SUPABASE_ANON_KEY", "").strip(),
    }


def _configured() -> bool:
    config = _public_auth_config()
    return bool(config["url"] and config["anon_key"])


@router.get("/login", response_class=HTMLResponse)
def login_page() -> HTMLResponse:
    config = json.dumps(_public_auth_config())
    html = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS Login</title></head><body>
    <main><h1>ATLAS</h1><p>Private account access</p>
    <button id="googleLogin">Continue with Google</button>
    <form id="emailLogin"><input id="email" type="email" autocomplete="email" required placeholder="Email"><button type="submit">Email code</button></form>
    <p id="authStatus"></p></main>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script>const cfg={config};const statusEl=document.getElementById('authStatus');
    if(!cfg.url||!cfg.anon_key)statusEl.textContent='Authentication is not configured.';
    const sb=(cfg.url&&cfg.anon_key)?supabase.createClient(cfg.url,cfg.anon_key):null;
    document.getElementById('googleLogin').onclick=async()=>{{if(!sb)return;await sb.auth.signInWithOAuth({{provider:'google',options:{{redirectTo:location.origin+'/auth/callback'}}}})}};
    document.getElementById('emailLogin').onsubmit=async(e)=>{{e.preventDefault();if(!sb)return;const email=document.getElementById('email').value;const r=await sb.auth.signInWithOtp({{email,options:{{emailRedirectTo:location.origin+'/auth/callback'}}}});statusEl.textContent=r.error?r.error.message:'Check your email for the sign-in link.'}};
    </script></body></html>'''
    return HTMLResponse(html)


@router.get("/auth/callback", response_class=HTMLResponse)
def auth_callback() -> HTMLResponse:
    config = json.dumps(_public_auth_config())
    return HTMLResponse(f'''<!doctype html><html><body><p>Signing you in to ATLAS…</p><script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script><script>
    const cfg={config};const sb=supabase.createClient(cfg.url,cfg.anon_key);(async()=>{{const {{data}}=await sb.auth.getSession();const token=data.session&&data.session.access_token;if(!token){{location.replace('/login');return;}}const r=await fetch('/auth/session',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{access_token:token}})}});location.replace(r.ok?'/app/dashboard':'/login');}})();
    </script></body></html>''')


@router.get("/auth/config")
def auth_config() -> dict[str, str]:
    return _public_auth_config()


@router.post("/auth/session")
def create_session(payload: SessionPayload) -> JSONResponse:
    verify_access_token(payload.access_token)
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        "atlas_session",
        payload.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,
        path="/",
    )
    return response


@router.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("atlas_session", path="/")
    return response


def _private_dashboard_response(request: Request) -> HTMLResponse | RedirectResponse:
    try:
        require_user(request)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    from app.dashboard.views import dashboard_view
    return dashboard_view()


@router.get("/dashboard", response_class=HTMLResponse)
def protected_dashboard(request: Request):
    return _private_dashboard_response(request)


@router.get("/app/dashboard", response_class=HTMLResponse)
def private_dashboard(request: Request):
    return _private_dashboard_response(request)
