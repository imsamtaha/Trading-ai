from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.dashboard.api import atlas_dashboard_state

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _demo_regime_from_technical(technical: dict | None) -> str:
    """Classify deterministic demo data without depending on MT5 or OpenAI."""
    context = technical or {}
    bullish = {"BULLISH", "UP", "UPTREND", "BUY", "LONG"}
    bearish = {"BEARISH", "DOWN", "DOWNTREND", "SELL", "SHORT"}
    values = {
        str(context.get(key, "")).strip().upper()
        for key in ("trend", "momentum", "macd_signal", "structure")
    }
    bull_votes = len(values & bullish)
    bear_votes = len(values & bearish)
    if max(bull_votes, bear_votes) >= 2 and bull_votes != bear_votes:
        return "TREND"
    return "RANGE"


def _analyze_demo_symbol(symbol: str) -> dict:
    """Return a safe dashboard row when external market services are unavailable."""
    return {
        "symbol": str(symbol),
        "canonical_symbol": str(symbol),
        "asset_class": "DEMO",
        "opportunity_score": 0.0,
        "price": 0.0,
        "spread_points": 0.0,
        "decision": {
            "decision": "WAIT",
            "bias": "NEUTRAL",
            "score": 0.0,
            "regime": "RANGE",
        },
        "quality": {
            "execution_confidence": 0.0,
            "signal_quality": "DEMO",
        },
        "timeframes": {},
    }


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
<title>ATLAS — Live Trading Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#06080d;--card:#0d131d;--line:#233044;--text:#f2f5f9;--muted:#8d9aad;--orange:#ff8a24;--green:#39d98a;--red:#ff6174;--yellow:#f6c85f;--blue:#72a7ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#172336 0,#06080d 42%);color:var(--text);font:14px Inter,system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1550px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.brand{display:flex;gap:12px;align-items:center}.logo{width:46px;height:46px;border:1px solid var(--orange);border-radius:15px;display:grid;place-items:center;font-weight:900;color:var(--orange);box-shadow:0 0 28px #ff8a2425}.title{font-size:24px;font-weight:900;letter-spacing:.06em}.sub{font-size:12px;color:var(--muted)}.badge{display:inline-flex;gap:7px;align-items:center;border:1px solid var(--line);padding:8px 11px;border-radius:999px;font-weight:800}.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 12px #39d98a88}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(6,1fr)}.split{grid-template-columns:1.65fr 1fr}.card{background:linear-gradient(180deg,#111824,#0b111a);border:1px solid var(--line);border-radius:17px;padding:16px;box-shadow:0 16px 45px #0006}.label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.11em}.big{font-size:25px;font-weight:900;margin-top:6px}.orange{color:var(--orange)}.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.blue{color:var(--blue)}.row{display:grid;grid-template-columns:1.25fr .8fr .7fr .7fr .65fr .65fr;gap:9px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}.row:last-child{border-bottom:0}.tablehead{font-size:10px;color:var(--muted);text-transform:uppercase}.symbol{font-weight:900}.mini{font-size:11px;color:var(--muted)}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px}.scorebar{height:6px;background:#1a2330;border-radius:99px;overflow:hidden}.scorefill{height:100%;background:var(--orange)}.pos{display:grid;grid-template-columns:1fr .7fr .55fr .75fr .65fr;gap:8px;padding:9px 0;border-bottom:1px solid var(--line)}.alert{padding:10px 12px;border:1px solid var(--line);border-radius:11px;margin-top:8px;background:#091019}.empty{color:var(--muted);padding:14px 0}.foot{margin-top:12px;color:var(--muted);font-size:11px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.notice{border-left:3px solid var(--orange);padding:10px 12px;background:#ff8a240b;border-radius:8px;color:#b9c3cf;margin-top:12px}@media(max-width:1200px){.stats{grid-template-columns:repeat(3,1fr)}.split{grid-template-columns:1fr}}@media(max-width:760px){main{padding:12px}.stats{grid-template-columns:1fr 1fr}.top{align-items:flex-start;flex-direction:column}.row{grid-template-columns:1fr 1fr}.row>*:nth-child(n+3){text-align:right}.pos{grid-template-columns:1fr 1fr}.title{font-size:19px}}
</style>
</head>
<body><main>
<div class="top"><div class="brand"><div class="logo">A</div><div><div class="title">ATLAS THE ULTIMATE</div><div class="sub">Live Trading Intelligence · Subscriber Observatory</div></div></div><div class="badge"><span class="dot"></span><span id="status">CONNECTING</span></div></div>
<div class="grid stats">
<div class="card"><div class="label">Account Type</div><div class="big" id="accountType">—</div></div>
<div class="card"><div class="label">Equity</div><div class="big" id="equity">—</div></div>
<div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div>
<div class="card"><div class="label">Floating P/L</div><div class="big" id="floating">—</div></div>
<div class="card"><div class="label">Open Positions</div><div class="big" id="openPositions">—</div></div>
<div class="card"><div class="label">Execution Gate</div><div class="big yellow" id="execution">—</div></div>
</div>
<div class="grid split" style="margin-top:12px">
<section class="card"><div class="label">ATLAS Opportunity Matrix</div><div id="signals"></div></section>
<section class="card"><div class="label">Verified Account</div><div id="account"></div><div class="label" style="margin-top:18px">Open Positions</div><div id="positions"></div></section>
</div>
<div class="grid split" style="margin-top:12px">
<section class="card"><div class="label">Selected Market Detail</div><div id="detail" class="empty">Select a market row.</div></section>
<section class="card"><div class="label">Priority Alerts</div><div id="alerts"></div></section>
</div>
<div class="notice" id="disclaimer">Read-only telemetry.</div>
<div class="foot"><span>Subscriber access: READ ONLY</span><span>Auto-refresh: 5 seconds</span><span>Last server update: <span id="updated">—</span></span></div>
</main>
<script>
let latest=null;
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\'':'&#39;','"':'&quot;'}[c]));
const money=(v,c='')=>v===null||v===undefined?'PRIVATE':`${Number(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}${c?` ${c}`:''}`;
const tone=v=>Number(v)>=0?'green':'red';
async function refresh(){try{const r=await fetch('/dashboard/state',{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();latest=d;const a=d.account||{};document.getElementById('status').textContent=d.verified_live_account?'VERIFIED LIVE':'ONLINE';document.getElementById('accountType').textContent=a.account_type||'—';document.getElementById('accountType').className='big '+(a.account_type==='REAL'?'green':'yellow');document.getElementById('equity').textContent=money(a.equity,a.currency);document.getElementById('balance').textContent=money(a.balance,a.currency);document.getElementById('floating').textContent=money(d.floating_position_pnl,a.currency);document.getElementById('floating').className='big '+tone(d.floating_position_pnl);document.getElementById('openPositions').textContent=d.open_positions??0;document.getElementById('execution').textContent=d.services.execution_gate;document.getElementById('execution').className='big '+(d.services.execution_gate==='ENABLED'?'green':'yellow');document.getElementById('account').innerHTML=`<div class="alert"><b>${esc(a.label)}</b><div class="mini">${esc(a.broker_company||'Broker')} · ${esc(a.server)}</div></div><div class="pos"><span>Account</span><b>${esc(a.login)}</b><span>Leverage</span><b>1:${esc(a.leverage||'—')}</b><span></span></div><div class="pos"><span>Margin free</span><b>${money(a.margin_free,a.currency)}</b><span>Margin level</span><b>${a.margin_level?Number(a.margin_level).toFixed(1)+'%':'—'}</b><span></span></div>`;
const rows=(d.symbols||[]).map(x=>{const s=x.decision,q=x.quality;return `<div class="row" onclick="show('${encodeURIComponent(x.symbol)}')"><div><div class="symbol">${esc(x.canonical_symbol||x.symbol)}</div><div class="mini">${esc(x.asset_class)} · broker ${esc(x.symbol)}</div></div><div><span class="tag ${s.bias==='BULLISH'?'green':s.bias==='BEARISH'?'red':''}">${esc(s.bias)}</span><div class="mini">${esc(s.decision)}</div></div><div>${Number(s.score||0).toFixed(1)}<div class="scorebar"><div class="scorefill" style="width:${Math.max(0,Math.min(100,Number(s.score||0)))}%"></div></div></div><div><b>${Number(q.execution_confidence||0).toFixed(1)}%</b><div class="mini">${esc(q.signal_quality)}</div></div><div>${Number(x.opportunity_score||0).toFixed(0)}</div><div>${Number(x.spread_points||0).toFixed(1)}</div></div>`}).join('');document.getElementById('signals').innerHTML='<div class="row tablehead"><div>Market</div><div>Bias / Action</div><div>Score</div><div>Confidence</div><div>Opportunity</div><div>Spread</div></div>'+rows;
const p=(d.positions||[]).map(x=>`<div class="pos"><div><b>${esc(x.symbol)}</b><div class="mini">${esc(x.direction)}</div></div><div>${x.volume}</div><div>${x.price_open}</div><div class="${tone(x.profit)}"><b>${Number(x.profit||0).toFixed(2)}</b></div><div class="mini">SL ${x.sl||'—'}<br>TP ${x.tp||'—'}</div></div>`).join('');document.getElementById('positions').innerHTML=p||'<div class="empty">No open positions.</div>';document.getElementById('alerts').innerHTML=(d.alerts||[]).length?d.alerts.map(x=>`<div class="alert"><b>${esc(x.symbol)}</b><div class="mini">${esc(x.message)}</div></div>`).join(''):'<div class="empty">No priority alerts.</div>';document.getElementById('disclaimer').textContent=d.disclaimer;document.getElementById('updated').textContent=d.timestamp?new Date(d.timestamp).toLocaleTimeString():'—';if(d.symbols?.length)show(encodeURIComponent(d.symbols[0].symbol));}catch(e){document.getElementById('status').textContent='OFFLINE';document.getElementById('alerts').innerHTML=`<div class="alert red">${esc(e.message)}</div>`}}
function show(encoded){if(!latest)return;const x=latest.symbols.find(v=>encodeURIComponent(v.symbol)===encoded);if(!x)return;const cells=Object.entries(x.timeframes||{}).map(([tf,v])=>`<div class="alert"><b>${tf}</b><div class="mini">Trend ${esc(v.trend)} · Momentum ${esc(v.momentum)} · MACD ${esc(v.macd)} · Structure ${esc(v.structure)} · Signal ${esc(v.signal)}</div></div>`).join('');document.getElementById('detail').innerHTML=`<div class="pos"><div><div class="label">Market</div><div class="big">${esc(x.canonical_symbol)}</div></div><div><div class="label">Price</div><b>${x.price}</b></div><div><div class="label">Score</div><b>${Number(x.decision.score||0).toFixed(1)}</b></div><div><div class="label">Confidence</div><b class="orange">${Number(x.quality.execution_confidence||0).toFixed(1)}%</b></div><div></div></div>${cells}`}
refresh();setInterval(refresh,5000);
</script></body></html>'''
