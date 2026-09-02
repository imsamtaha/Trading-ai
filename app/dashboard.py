from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.dashboard.api import atlas_dashboard_state

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/state")
def state():
    return atlas_dashboard_state()


@router.get("", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS — Trading Intelligence Hub</title>
<style>
:root{color-scheme:dark;--bg:#070a10;--card:#0d121b;--panel:#111824;--line:#263243;--text:#edf2f7;--muted:#8b98aa;--orange:#ff8a24;--green:#35d07f;--red:#ff6575;--yellow:#f4c95d;--blue:#6ea8fe}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0%,#182333 0,#070a10 40%),var(--bg);color:var(--text);font:14px Inter,system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1500px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:18px}.brand{display:flex;align-items:center;gap:12px}.logo{width:40px;height:40px;border:1px solid var(--orange);border-radius:12px;display:grid;place-items:center;color:var(--orange);font-weight:900}.title{font-size:24px;font-weight:900;letter-spacing:.04em}.sub{color:var(--muted);font-size:12px}.status{display:flex;align-items:center;gap:8px;font-weight:800}.dot{width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 14px #35d07f66}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(5,1fr)}.wide{grid-template-columns:1.7fr 1fr}.card{background:linear-gradient(180deg,#111824,#0d121b);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 14px 40px #0005}.label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.1em}.big{font-size:25px;font-weight:900;margin-top:6px}.orange{color:var(--orange)}.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.blue{color:var(--blue)}.row{display:grid;grid-template-columns:1.2fr .8fr .8fr .8fr .8fr;gap:9px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}.row:last-child{border-bottom:0}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px}.tablehead{color:var(--muted);font-size:10px;text-transform:uppercase}.symbol{font-weight:900}.scorebar{height:7px;background:#1b2432;border-radius:99px;overflow:hidden}.scorefill{height:100%;background:var(--orange)}.mini{font-size:11px;color:var(--muted)}.alert{padding:10px 12px;border:1px solid var(--line);border-radius:10px;margin-top:8px;background:#0b1018}.empty{color:var(--muted);padding:14px 0}.foot{color:var(--muted);font-size:11px;margin-top:10px;display:flex;justify-content:space-between;gap:12px}@media(max-width:1100px){.stats{grid-template-columns:repeat(2,1fr)}.wide{grid-template-columns:1fr}}@media(max-width:760px){main{padding:12px}.stats{grid-template-columns:1fr}.top{align-items:flex-start}.row{grid-template-columns:1fr 1fr}.row>*:nth-child(n+3){text-align:right}.title{font-size:19px}}
</style>
</head>
<body><main>
<div class="top"><div class="brand"><div class="logo">A</div><div><div class="title">ATLAS</div><div class="sub">Trading Intelligence Hub · FxPro MT5 Demo</div></div></div><div class="status"><span class="dot"></span><span id="status">CONNECTING</span></div></div>
<div class="grid stats">
<div class="card"><div class="label">Account Equity</div><div class="big" id="equity">—</div></div>
<div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div>
<div class="card"><div class="label">Broker</div><div class="big orange" id="broker">—</div></div>
<div class="card"><div class="label">Environment</div><div class="big yellow" id="mode">—</div></div>
<div class="card"><div class="label">Instruments</div><div class="big" id="count">—</div></div>
</div>
<div class="grid wide" style="margin-top:12px">
<section class="card"><div class="label">ATLAS Signal Matrix</div><div id="signals"></div></section>
<section class="card"><div class="label">System Health</div><div id="system"></div><div class="label" style="margin-top:18px">Priority Alerts</div><div id="alerts"></div></section>
</div>
<div class="card" style="margin-top:12px"><div class="label">Selected Market Detail</div><div id="detail" class="empty">Select a symbol row to inspect its multi-timeframe state.</div></div>
<div class="foot"><span>Auto-refresh: 5 seconds</span><span>Live execution: disabled</span><span>Last update: <span id="updated">—</span></span></div>
</main>
<script>
let latest=null;
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\'':'&#39;','"':'&quot;'}[c]));
const cls=v=>Number(v)>=0?'green':'red';
const pct=v=>`${Number(v||0).toFixed(1)}%`;
async function refresh(){try{const r=await fetch('/dashboard/state',{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();latest=d;document.getElementById('status').textContent=d.status;document.getElementById('broker').textContent=d.broker;document.getElementById('mode').textContent=d.mode;document.getElementById('count').textContent=d.symbols.length;document.getElementById('equity').textContent=Number(d.account.equity||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});document.getElementById('balance').textContent=Number(d.account.balance||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});const rows=d.symbols.map(x=>{const q=x.quality,s=x.decision;return `<div class="row" onclick="show('${encodeURIComponent(x.symbol)}')"><div><div class="symbol">${esc(x.symbol)}</div><div class="mini">${esc(s.regime)} · ${esc(s.mtf_alignment)}</div></div><div><span class="tag ${s.bias==='BULLISH'?'green':s.bias==='BEARISH'?'red':''}">${esc(s.bias)}</span><div class="mini">${esc(s.decision)}</div></div><div><div>${Number(s.score||0).toFixed(1)}</div><div class="scorebar"><div class="scorefill" style="width:${Math.max(0,Math.min(100,Number(s.score||0)))}%"></div></div></div><div><b>${pct(q.execution_confidence)}</b><div class="mini">${esc(q.signal_quality)}</div></div><div class="${s.risk_level==='HIGH'||s.risk_level==='EXTREME'?'red':'green'}">${esc(s.risk_level)}</div></div>`}).join('');document.getElementById('signals').innerHTML='<div class="row tablehead"><div>Symbol</div><div>Bias / Action</div><div>Score</div><div>Execution</div><div>Risk</div></div>'+rows;document.getElementById('system').innerHTML=`<div class="row"><span>MT5</span><b>${esc(d.services.mt5)}</b></div><div class="row"><span>Supabase</span><b>${esc(d.services.supabase)}</b></div><div class="row"><span>Server</span><b>${esc(d.server||'—')}</b></div><div class="row"><span>Login</span><b>#${esc(d.account.login||'—')}</b></div><div class="row"><span>Live trading</span><b class="${d.services.live_trading?'red':'green'}">${d.services.live_trading?'ENABLED':'DISABLED'}</b></div>`;document.getElementById('alerts').innerHTML=d.alerts.length?d.alerts.map(a=>`<div class="alert"><b>${esc(a.symbol)}</b><div class="mini">${esc(a.message)}</div></div>`).join(''):'<div class="empty">No priority alerts.</div>';document.getElementById('updated').textContent=new Date().toLocaleTimeString();if(d.symbols.length)show(encodeURIComponent(d.symbols[0].symbol));}catch(err){document.getElementById('status').textContent='OFFLINE';document.getElementById('alerts').innerHTML=`<div class="alert red">Dashboard unavailable: ${esc(err.message)}</div>`}}
function show(encoded){if(!latest)return;const x=latest.symbols.find(v=>encodeURIComponent(v.symbol)===encoded);if(!x)return;const cells=Object.entries(x.timeframes).map(([tf,v])=>`<div class="alert"><b>${tf}</b><div class="row" style="grid-template-columns:repeat(5,1fr)"><span>${esc(v.trend)}</span><span>${esc(v.momentum)}</span><span>${esc(v.macd)}</span><span>${esc(v.structure)}</span><span>${esc(v.signal)}</span></div></div>`).join('');document.getElementById('detail').innerHTML=`<div class="row" style="grid-template-columns:1fr 1fr 1fr 1fr"><div><div class="label">Symbol</div><div class="big">${esc(x.symbol)}</div></div><div><div class="label">Price</div><div class="big">${x.price}</div></div><div><div class="label">ATLAS Score</div><div class="big">${Number(x.decision.score).toFixed(1)}</div></div><div><div class="label">Execution Confidence</div><div class="big orange">${pct(x.quality.execution_confidence)}</div></div></div><div class="mini" style="margin:10px 0">5m / 15m / 30m / 1h state</div>${cells}`;}
refresh();setInterval(refresh,5000);
</script></body></html>'''
