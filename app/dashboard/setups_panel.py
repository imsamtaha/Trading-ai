from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles
from app.strategies.router import generate_strategy_candidate

router = APIRouter()

DEFAULT_SETUP_SYMBOLS = ("XAUUSD", "XAGUSD", "EURUSD", "XRPUSDT", "SOLUSDT")
_ALLOWED_INTERVALS = {"5m", "15m", "30m", "1h"}
_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}


def _symbols() -> tuple[str, ...]:
    raw = os.getenv("ATLAS_SETUP_SYMBOLS", ",".join(DEFAULT_SETUP_SYMBOLS))
    symbols = tuple(dict.fromkeys(part.strip().upper() for part in raw.split(",") if part.strip()))
    return symbols[:12] or DEFAULT_SETUP_SYMBOLS


def _interval() -> str:
    value = os.getenv("ATLAS_SETUP_INTERVAL", "15m").strip().lower()
    return value if value in _ALLOWED_INTERVALS else "15m"


def _scan_setups() -> dict[str, Any]:
    strategy_mode = os.getenv("ATLAS_STRATEGY_MODE", "BALANCED").strip().upper() or "BALANCED"
    interval = _interval()
    balance = float(os.getenv("ATLAS_DEMO_ACCOUNT_EQUITY", "10000"))
    results: list[dict[str, Any]] = []
    errors = 0

    for symbol in _symbols():
        try:
            market = get_candles(symbol, interval, 120)
            technical = analyze_candles(market["candles"])
            structure = analyze_structure(market["candles"])
            candidate = generate_strategy_candidate(
                symbol,
                technical,
                structure,
                mode=strategy_mode,
                account_balance=balance,
            )
            if candidate is None:
                results.append({"symbol": symbol, "status": "WAIT", "qualified": False})
                continue
            item = candidate.to_dict()
            item["status"] = "ACTIVE_SETUP" if item.get("qualified") else "WATCH"
            results.append(item)
        except Exception:
            errors += 1
            results.append({"symbol": symbol, "status": "UNAVAILABLE", "qualified": False})

    active = [item for item in results if item.get("qualified") is True]
    watch = [item for item in results if item.get("status") == "WATCH"]
    return {
        "mode": "LIVE_DEMO",
        "broker_orders": False,
        "demo_execution": True,
        "execution": "simulated_demo",
        "strategy_mode": strategy_mode,

        "interval": interval,
        "active_count": len(active),
        "watch_count": len(watch),
        "errors": errors,
        "setups": active,
        "watchlist": watch,
        "scanned": len(results),
        "disclaimer": "Live demo setup scanner with ATLAS simulated demo execution. Real-money broker orders are disabled.",
    }


@router.get("/dashboard/active-setups")
def active_setups() -> dict[str, Any]:
    now = time.monotonic()
    cached = _CACHE.get("payload")
    if cached is not None and now < float(_CACHE.get("expires_at", 0.0)):
        return cached

    payload = _scan_setups()
    ttl = max(10, min(120, int(os.getenv("ATLAS_SETUP_CACHE_SECONDS", "45"))))
    _CACHE["payload"] = payload
    _CACHE["expires_at"] = now + ttl
    return payload


@router.get("/ui/setups-panel.js", include_in_schema=False)
def setups_panel_script() -> Response:
    return Response(SCRIPT, media_type="application/javascript")


SCRIPT = r"""
(()=>{
const root=document.querySelector('.shell')||document.querySelector('main')||document.body;
if(!root||document.getElementById('active-setups'))return;

const style=document.createElement('style');
style.textContent=`
.active-setups{margin:0 0 18px;border-color:#ff7a1a55}
.setup-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.setup-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}
.setup-card{border:1px solid var(--line);border-radius:14px;padding:13px;background:#080d14aa}
.setup-card.active{border-color:#39d98a55}
.setup-card.watch{border-color:#f6c45355}
`;

document.head.append(style);

const panel=document.createElement('section');
panel.className='card active-setups';
panel.id='active-setups';
panel.innerHTML=`
<div class="setup-head">
  <div>
    <div class="label">ACTIVE SETUPS</div>
    <div class="demo-title">ATLAS Live Demo Setup Engine</div>
    <div class="mini">Real-time MT5 demo analysis · simulated ATLAS demo execution · real-money orders off</div>
  </div>
  <div class="demo-status stale" id="setupStatus"><span class="demo-dot"></span><span id="setupStatusText">SCANNING</span></div>
</div>
<div class="setup-grid" id="setupGrid"><div class="mini">Scanning current demo setups…</div></div>
<div class="demo-foot" id="setupMeta">Mode: —</div>`;

const demo=document.getElementById('demo-session');
if(demo)demo.insertAdjacentElement('afterend',panel);
else{
  const hero=root.querySelector('.hero');
  if(hero)hero.insertAdjacentElement('afterend',panel);else root.prepend(panel);
}

const esc=v=>String(v==null?'':v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const num=v=>Number.isFinite(Number(v))?Number(v).toFixed(2):'—';
function status(text,kind){
  const box=document.getElementById('setupStatus');
  document.getElementById('setupStatusText').textContent=text;
  box.className='demo-status '+kind;
}

function card(item,kind){
  const direction=esc(item.direction||'WAIT');
  const klass=esc(item.classification||'—');
  const confidence=num(item.confidence);
  const strategy=esc(item.strategy||'No qualified strategy');
  const rr=num(item.risk_reward);
  const levels=item.entry!=null
    ? `<div class="mini" style="margin-top:8px">Entry <b>${num(item.entry)}</b> · SL <b>${num(item.stop_loss)}</b> · TP <b>${num(item.take_profit)}</b></div>`
    : '';
  return `<div class="setup-card ${kind}">
    <div class="label">${esc(item.symbol||'UNKNOWN')}</div>
    <div style="font-size:20px;font-weight:950;margin-top:5px">${direction} · ${klass}</div>
    <div class="mini" style="margin-top:5px">${strategy} · Confidence ${confidence}% · R:R ${rr}</div>
    ${levels}
  </div>`;
}

async function refreshSetups(){
  try{
    const response=await fetch('/dashboard/active-setups',{cache:'no-store'});
    if(!response.ok)throw new Error('setup scan unavailable');
    const data=await response.json();
    const active=Array.isArray(data.setups)?data.setups:[];
    const watch=Array.isArray(data.watchlist)?data.watchlist:[];
    const items=active.length?active.slice(0,6):watch.slice(0,6);
    const grid=document.getElementById('setupGrid');

    if(!items.length){
      grid.innerHTML='<div class="setup-card"><div class="label">NO QUALIFIED SETUP</div><div class="mini" style="margin-top:7px">ATLAS is waiting for a demo setup that satisfies the strategy and risk rules.</div></div>';
    }else{
      grid.innerHTML=items.map(item=>card(item,active.length?'active':'watch')).join('');
    }

    document.getElementById('setupMeta').textContent=
      `Mode: ${data.mode||'LIVE_DEMO'} · Strategy: ${data.strategy_mode||'BALANCED'} · Interval: ${data.interval||'15m'} · Active: ${data.active_count||0} · Watch: ${data.watch_count||0} · PAPER · Real-money: OFF`;
    status(active.length?'ACTIVE':'MONITORING',active.length?'online':'stale');
  }catch(error){
    status('UNAVAILABLE','offline');
    document.getElementById('setupGrid').innerHTML=
      '<div class="setup-card"><div class="label">SETUP SCAN UNAVAILABLE</div><div class="mini" style="margin-top:7px">ATLAS could not refresh demo setups right now.</div></div>';
  }
}

refreshSetups();
setInterval(refreshSetups,45000);
})();
"""
