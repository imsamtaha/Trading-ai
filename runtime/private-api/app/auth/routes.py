from __future__ import annotations

import json
import os

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth.supabase_auth import verify_access_token, supabase_publishable_key
from app.runtime_control.analytics import record_sign_in, record_sign_out

router = APIRouter(tags=["auth"])


class SessionPayload(BaseModel):
    access_token: str


def _public_auth_config() -> dict[str, str]:
    return {
        "url": os.getenv("SUPABASE_URL", "").strip(),
        "anon_key": supabase_publishable_key(),
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
    }


def _configured() -> bool:
    config = _public_auth_config()
    return bool(config["url"] and config["anon_key"])


@router.get("/login", response_class=HTMLResponse)
def login_page() -> HTMLResponse:
    config = json.dumps(_public_auth_config())
    html = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS Login</title></head><body>
    <main><h1>ATLAS</h1><p>Private account access</p>
    <div><span>Continue with Google</span><div id="googleLogin"></div></div>
    <form id="emailLogin"><input id="email" type="email" autocomplete="email" required placeholder="Email"><button type="submit">Email code</button></form>
    <p id="authStatus"></p></main>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <script>const cfg={config};const statusEl=document.getElementById('authStatus');
    if(!cfg.url||!cfg.anon_key)statusEl.textContent='Authentication is not configured.';
    const sb=(cfg.url&&cfg.anon_key)?supabase.createClient(cfg.url,cfg.anon_key):null;
    async function completeGoogleLogin(response){{if(!sb||!response||!response.credential)return;statusEl.textContent='Signing in…';const r=await sb.auth.signInWithIdToken({{provider:'google',token:response.credential}});if(r.error){{statusEl.textContent=r.error.message;return;}}const token=r.data.session&&r.data.session.access_token;if(!token){{statusEl.textContent='Google sign-in did not create a session.';return;}}const session=await fetch('/auth/session',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{access_token:token}})}});location.replace(session.ok?'/api/me':'/login');}}
    window.addEventListener('load',()=>{{if(cfg.google_client_id&&window.google&&google.accounts&&google.accounts.id){{google.accounts.id.initialize({{client_id:cfg.google_client_id,callback:completeGoogleLogin,use_fedcm_for_prompt:true}});google.accounts.id.renderButton(document.getElementById('googleLogin'),{{theme:'outline',size:'large',text:'continue_with'}});}}else if(!cfg.google_client_id){{statusEl.textContent='Google sign-in is not configured.';}}}});
    document.getElementById('emailLogin').onsubmit=async(e)=>{{e.preventDefault();if(!sb)return;const email=document.getElementById('email').value;const r=await sb.auth.signInWithOtp({{email,options:{{emailRedirectTo:location.origin+'/auth/callback'}}}});statusEl.textContent=r.error?r.error.message:'Check your email for the sign-in link.'}};
    </script></body></html>'''
    return HTMLResponse(html)


@router.get("/auth/callback", response_class=HTMLResponse)
def auth_callback() -> HTMLResponse:
    config = json.dumps(_public_auth_config())
    return HTMLResponse(f'''<!doctype html><html><body><p>Signing you in to ATLAS…</p><script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script><script>
    const cfg={config};const sb=supabase.createClient(cfg.url,cfg.anon_key);(async()=>{{const {{data}}=await sb.auth.getSession();const token=data.session&&data.session.access_token;if(!token){{location.replace('/login');return;}}const r=await fetch('/auth/session',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{access_token:token}})}});location.replace(r.ok?'/api/me':'/login');}})();
    </script></body></html>''')


@router.get("/auth/config")
def auth_config() -> dict[str, str]:
    return _public_auth_config()


@router.post("/auth/session")
def create_session(payload: SessionPayload) -> JSONResponse:
    user = verify_access_token(payload.access_token)
    owner_email = os.getenv("ATLAS_OWNER_EMAIL", "").strip().lower()
    is_owner = bool(owner_email and user.email and user.email.strip().lower() == owner_email)
    record_sign_in(user.user_id, is_owner=is_owner)
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
    record_sign_out()
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("atlas_session", path="/")
    return response


@router.api_route("/dashboard", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/app/dashboard", methods=["GET", "HEAD"], include_in_schema=False)
def retired_dashboard():
    return Response(status_code=410, headers={"Cache-Control": "no-store"})
