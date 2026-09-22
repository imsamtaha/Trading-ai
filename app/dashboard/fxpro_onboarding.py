from __future__ import annotations

import html
import json
import os
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(tags=["fxpro-onboarding"])

FXPRO_CONNECT_PATH = "/connect/fxpro-mt5"
LEGACY_FXPRO_CONNECT_PATH = "/connect/fxpro"
DEFAULT_FXPRO_URL = "https://www.fxpro.com/"


def _external_https_url(value: str | None, fallback: str = DEFAULT_FXPRO_URL) -> str:
    candidate = (value or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme == "https" and parsed.netloc:
        return candidate
    return fallback


def fxpro_open_account_url() -> str:
    """Return the configured FxPro partner/open-account destination.

    Production can set ATLAS_FXPRO_PARTNER_URL to an approved FxPro partner
    link without committing affiliate identifiers to source control.
    """

    return _external_https_url(os.getenv("ATLAS_FXPRO_PARTNER_URL"))


def fxpro_entry_card() -> str:
    return """
<section id="fxpro-entry" class="card fxpro-entry-card" style="margin-top:18px">
  <div class="label">FXPRO MT5 ENTRY</div>
  <div class="fxpro-entry-grid">
    <div>
      <h2 style="font-size:clamp(28px,4vw,46px);margin:8px 0 8px">Connect with FxPro MT5.</h2>
      <p class="mini" style="font-size:13px;line-height:1.65;max-width:760px">
        Start from your FxPro MT5 demo account, then enter ATLAS through the dedicated MT5 onboarding flow.
        The current connection flow is demo/read-only and never asks for a broker password.
      </p>
    </div>
    <div class="fxpro-entry-actions">
      <a class="btn atlas-3d" href="/connect/fxpro-mt5">Connect with FxPro MT5</a>
    </div>
  </div>
</section>
<style>
.fxpro-entry-grid{display:grid;grid-template-columns:1.5fr auto;gap:18px;align-items:center}
.fxpro-entry-actions{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}
@media(max-width:760px){.fxpro-entry-grid{grid-template-columns:1fr}.fxpro-entry-actions{justify-content:stretch}.fxpro-entry-actions .btn{width:100%;text-align:center}}
</style>
"""


def _page() -> str:
    fxpro_url = html.escape(fxpro_open_account_url(), quote=True)
    fxpro_url_json = json.dumps(fxpro_open_account_url())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0f17">
<title>Connect with FxPro MT5 | ATLAS</title>
<style>
:root{{color-scheme:dark;--bg:#070a0f;--card:#0f1722;--line:#2b3849;--text:#f5f1e9;--muted:#9fa9b7;--orange:#ff7a1a;--green:#3bd58b}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 50% -20%,#1c2a3e 0,#070a0f 48%);color:var(--text);font:16px Inter,system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:22px 16px calc(36px + env(safe-area-inset-bottom))}}
.brand{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px}}.brand b{{letter-spacing:.08em}}.brand a{{color:var(--muted);text-decoration:none;font-size:14px}}
.card{{background:linear-gradient(180deg,#121b28,#0b121b);border:1px solid var(--line);border-radius:22px;padding:20px;box-shadow:0 22px 60px #0008;margin-bottom:14px}}
.eyebrow{{color:var(--orange);font-size:12px;font-weight:900;letter-spacing:.14em}}h1{{font-size:clamp(34px,10vw,56px);line-height:1.02;margin:10px 0 12px}}p{{color:var(--muted);line-height:1.6}}
.steps{{display:grid;gap:10px;margin:18px 0}}.step{{display:grid;grid-template-columns:38px 1fr;gap:12px;align-items:start;padding:12px;border:1px solid var(--line);border-radius:15px;background:#ffffff03}}
.num{{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:#ff7a1715;color:var(--orange);font-weight:900}}
.step b{{display:block;margin:1px 0 4px}}.step span{{color:var(--muted);font-size:13px;line-height:1.45}}
.actions{{display:grid;gap:10px}}.button{{appearance:none;border:1px solid transparent;border-radius:14px;padding:15px 16px;font:inherit;font-weight:900;text-align:center;text-decoration:none;cursor:pointer}}
.primary{{background:var(--orange);color:#090b0e}}.secondary{{background:#111b28;color:var(--text);border-color:var(--line)}}
.panel{{display:none;margin-top:14px}}.panel.open{{display:block}}
label{{display:block;font-weight:800;margin:14px 0 7px}}input{{width:100%;border:1px solid #39485d;background:#09111b;color:var(--text);border-radius:13px;padding:14px 13px;font:inherit;outline:none}}input:focus{{border-color:#f5f1e9}}
.mode-pill{{display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid #3bd58b55;background:#3bd58b0d;border-radius:13px;padding:12px 13px;margin-top:8px}}.mode-pill strong{{color:#ccebdd}}.mode-pill span{{font-size:12px;color:var(--muted)}}
.notice{{font-size:13px;border-left:3px solid var(--orange);padding:10px 12px;background:#ff7a1710;border-radius:9px;margin:14px 0;color:#c5ccd5}}
.success{{display:none;border:1px solid #3bd58b55;background:#3bd58b0d;border-radius:14px;padding:13px;margin-top:12px;color:#ccebdd}}.success.show{{display:block}}
.micro{{font-size:12px;color:#7f8a99;margin-top:12px}}.divider{{height:1px;background:var(--line);margin:18px 0}}
@media(min-width:620px){{.actions.two{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<main>
  <div class="brand"><b>JUST AI / ATLAS</b><a href="/">← ATLAS</a></div>

  <section class="card">
    <div class="eyebrow">FXPRO MT5 ENTRY</div>
    <h1>Connect with FxPro MT5</h1>
    <p>Use your FxPro MT5 demo account as the entry point into ATLAS. FxPro remains the broker and ATLAS remains the intelligence layer.</p>

    <div class="steps">
      <div class="step"><div class="num">1</div><div><b>Open or create FxPro MT5</b><span>Use the FxPro app or mobile site and choose an MT5 demo account.</span></div></div>
      <div class="step"><div class="num">2</div><div><b>Return to ATLAS</b><span>Enter the MT5 account number and the exact FxPro MT5 server name shown for the demo account.</span></div></div>
      <div class="step"><div class="num">3</div><div><b>Enter ATLAS</b><span>ATLAS keeps this onboarding draft only in the current browser session. Broker execution is not enabled by this page.</span></div></div>
    </div>

    <div class="actions two">
      <a id="openFxPro" class="button primary" href="{fxpro_url}" target="_blank" rel="noopener noreferrer">Open FxPro MT5 ↗</a>
      <button id="existing" class="button secondary" type="button">I already have FxPro MT5</button>
    </div>
    <p class="micro">The FxPro destination can be replaced with an approved partner/referral URL using ATLAS_FXPRO_PARTNER_URL.</p>
  </section>

  <section id="connectPanel" class="card panel" aria-labelledby="connectTitle">
    <div class="eyebrow">FXPRO MT5 → ATLAS</div>
    <h2 id="connectTitle">Prepare your FxPro MT5 demo connection</h2>
    <p>Current ATLAS onboarding accepts demo account metadata only. It does not request or store an FxPro/MT5 password.</p>

    <div class="mode-pill">
      <strong>Demo · Read-only onboarding</strong>
      <span>Live connection is not enabled here.</span>
    </div>

    <form id="fxproForm">
      <label for="login">MT5 account number</label>
      <input id="login" name="login" inputmode="numeric" autocomplete="off" placeholder="Example: 592031391" maxlength="20" required>

      <label for="server">FxPro MT5 server name</label>
      <input id="server" name="server" autocomplete="off" placeholder="Example: FxPro-MT5 Demo" maxlength="80" required>

      <div class="notice"><b>Security:</b> Do not enter your FxPro password, MT5 master password, investor password, PIN, recovery code, or payment details on this page.</div>

      <button class="button primary" type="submit" style="width:100%">Continue with FxPro MT5</button>
    </form>

    <div id="saved" class="success" role="status">
      <b>FxPro MT5 demo entry prepared.</b>
      <div style="margin-top:5px">Your account number and server are kept only for this browser session. This is onboarding metadata, not broker authentication.</div>
      <div class="divider"></div>
      <a class="button secondary" href="/" style="display:block">Enter ATLAS dashboard →</a>
    </div>
  </section>
</main>
<script>
const fxproUrl={fxpro_url_json};
const panel=document.getElementById('connectPanel');
const form=document.getElementById('fxproForm');
const saved=document.getElementById('saved');
document.getElementById('existing').addEventListener('click',()=>{{panel.classList.add('open');panel.scrollIntoView({{behavior:'smooth',block:'start'}});}});
document.getElementById('openFxPro').addEventListener('click',()=>{{try{{sessionStorage.setItem('atlas.fxpro.mt5.returnPending','1')}}catch{{}}}});
form.addEventListener('submit',event=>{{
  event.preventDefault();
  const login=document.getElementById('login').value.trim();
  const server=document.getElementById('server').value.trim();
  if(!/^\\d{{4,20}}$/.test(login)){{document.getElementById('login').setCustomValidity('Enter a valid MT5 account number.');document.getElementById('login').reportValidity();return;}}
  document.getElementById('login').setCustomValidity('');
  if(server.length<3||!/fxpro/i.test(server)){{document.getElementById('server').setCustomValidity('Enter the FxPro MT5 server name shown for your demo account.');document.getElementById('server').reportValidity();return;}}
  document.getElementById('server').setCustomValidity('');
  try{{sessionStorage.setItem('atlas.fxpro.mt5.connectionDraft',JSON.stringify({{broker:'FxPro',platform:'MT5',mode:'demo',login,server,savedAt:new Date().toISOString()}}));sessionStorage.removeItem('atlas.fxpro.mt5.returnPending')}}catch{{}}
  saved.classList.add('show');
  saved.scrollIntoView({{behavior:'smooth',block:'nearest'}});
}});
try{{
  if(sessionStorage.getItem('atlas.fxpro.mt5.returnPending')==='1'){{panel.classList.add('open')}}
  const prior=JSON.parse(sessionStorage.getItem('atlas.fxpro.mt5.connectionDraft')||'null');
  if(prior&&prior.login&&prior.server){{document.getElementById('login').value=prior.login;document.getElementById('server').value=prior.server;}}
}}catch{{}}
</script>
</body>
</html>"""


@router.get(LEGACY_FXPRO_CONNECT_PATH, include_in_schema=False)
def legacy_fxpro_mobile_entry() -> RedirectResponse:
    return RedirectResponse(url=FXPRO_CONNECT_PATH, status_code=308)


@router.get(FXPRO_CONNECT_PATH, response_class=HTMLResponse, include_in_schema=False)
def fxpro_mt5_entry() -> HTMLResponse:
    return HTMLResponse(_page())
