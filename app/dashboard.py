from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.data.market import get_price
from app.paper_trading.engine import PersistentPaperTradingEngine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ACCOUNT_ID = 3
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


@router.get("/state")
def dashboard_state(account_id: int = ACCOUNT_ID):
    try:
        engine = PersistentPaperTradingEngine(account_id)
        account = engine.account()
        positions = engine.positions()

        prices = {}
        for symbol in SYMBOLS:
            data = get_price(symbol)
            prices[symbol] = float(data["price"])

        equity = engine.calculate_equity(prices)
        return {
            "status": "LIVE",
            "mode": "paper_trading",
            "account": account,
            "prices": prices,
            "equity": equity,
            "positions": positions,
            "atlas": {
                "decision": "WAIT",
                "strength": "Monitoring",
                "alignment": "—",
            },
            "risk": {
                "level": "LOW",
                "daily_risk_percent": 0.0,
                "max_daily_loss_percent": 2.0,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Hub — Trader Cockpit</title>
<style>
:root{color-scheme:dark;--bg:#090a0c;--panel:#111316;--panel2:#15171a;--line:#292c31;--text:#f4f4f5;--muted:#92969f;--orange:#ff8a1f;--green:#35d07f;--red:#ff6575;--silver:#c8ccd2}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 85% -10%,#25201a 0,transparent 34%),var(--bg);color:var(--text);font:14px Inter,system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1380px;margin:auto;padding:22px}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.brand{display:flex;align-items:center;gap:11px}.logo{width:38px;height:38px;border:1px solid #5a5e65;border-radius:50%;display:grid;place-items:center;font-weight:900;color:var(--orange);box-shadow:0 0 22px #ff8a1f22}.name{font-size:20px;font-weight:850;letter-spacing:.02em}.sub{color:var(--muted);font-size:11px;margin-top:2px}.live{display:flex;align-items:center;gap:8px;color:var(--green);font-weight:700;font-size:12px}.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 10px #35d07f88}.grid{display:grid;gap:12px}.stats{grid-template-columns:2fr 1.1fr 1.1fr 1.1fr}.card{background:linear-gradient(145deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:16px;padding:17px;box-shadow:0 10px 30px #00000022}.label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.12em}.value{font-size:27px;font-weight:850;margin-top:7px}.change{font-size:12px;margin-top:5px}.green{color:var(--green)}.red{color:var(--red)}.orange{color:var(--orange)}.main{grid-template-columns:1.35fr .85fr;margin-top:12px}.atlas{position:relative;overflow:hidden}.atlas:after{content:"";position:absolute;width:180px;height:180px;border-radius:50%;right:-90px;top:-90px;border:1px solid #ff8a1f33}.decision{display:flex;align-items:center;justify-content:space-between;margin-top:13px}.decision strong{font-size:30px;letter-spacing:.04em}.pill{border:1px solid #3a3d43;border-radius:999px;padding:6px 10px;font-size:11px;color:var(--silver)}.frames{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:15px}.frame{background:#0d0f11;border:1px solid var(--line);border-radius:10px;padding:9px;text-align:center}.frame b{display:block;margin-top:4px}.riskline{display:flex;align-items:center;justify-content:space-between;margin-top:15px;padding-top:13px;border-top:1px solid var(--line)}.riskbadge{padding:7px 12px;border-radius:999px;border:1px solid #35d07f55;color:var(--green);font-weight:800;font-size:11px}.market{margin-top:12px}.row{display:grid;grid-template-columns:1.2fr 1fr .7fr 1fr;gap:10px;padding:12px 0;border-bottom:1px solid var(--line);align-items:center}.row:last-child{border-bottom:0}.muted{color:var(--muted);font-size:12px}.positions{margin-top:12px}.empty{padding:18px 0;color:var(--muted)}.nav{display:flex;gap:8px;margin-top:16px;overflow:auto}.nav span{padding:9px 13px;border:1px solid var(--line);border-radius:10px;color:var(--muted);white-space:nowrap}.nav .active{color:var(--text);border-color:#ff8a1f66;background:#ff8a1f12}.footer{margin-top:12px;color:var(--muted);font-size:11px}@media(max-width:850px){main{padding:13px}.stats,.main{grid-template-columns:1fr 1fr}.stats .card:first-child{grid-column:span 2}.row{grid-template-columns:1fr 1fr}.row>*:nth-child(n+3){text-align:right}}@media(max-width:520px){.stats,.main{grid-template-columns:1fr}.stats .card:first-child{grid-column:auto}.value{font-size:24px}.frames{grid-template-columns:repeat(4,1fr)}}
</style></head>
<body><main>
<header class="top"><div class="brand"><div class="logo">J</div><div><div class="name">TRADING HUB</div><div class="sub">AI Trading Operating System · Trader Cockpit</div></div></div><div class="live"><span class="dot"></span><span id="status">CONNECTING</span></div></header>
<section class="grid stats">
<div class="card"><div class="label">Account Value</div><div class="value" id="equity">—</div><div class="change" id="today">Paper account</div></div>
<div class="card"><div class="label">Today P/L</div><div class="value" id="pnl">—</div></div>
<div class="card"><div class="label">Positions</div><div class="value" id="count">—</div></div>
<div class="card"><div class="label">Risk</div><div class="value green" id="risk">LOW</div></div>
</section>
<section class="grid main">
<div class="card atlas"><div class="label">ATLAS Intelligence</div><div class="decision"><div><strong id="decision">WAIT</strong><div class="muted" id="strength">Monitoring market conditions</div></div><span class="pill" id="alignment">No active alignment</span></div><div class="frames"><div class="frame"><span class="muted">5m</span><b>—</b></div><div class="frame"><span class="muted">15m</span><b>—</b></div><div class="frame"><span class="muted">30m</span><b>—</b></div><div class="frame"><span class="muted">1H</span><b>—</b></div></div></div>
<div class="card"><div class="label">Risk Control</div><div class="decision"><div><strong id="riskPct">0.0%</strong><div class="muted">Daily risk used</div></div><span class="riskbadge" id="riskBadge">SAFE</span></div><div class="riskline"><span class="muted">Maximum daily loss</span><b>2.0%</b></div><div class="riskline"><span class="muted">Execution</span><b>Paper</b></div></div>
</section>
<section class="card market"><div class="label">Market Watch</div><div id="markets"></div></section>
<section class="card positions"><div class="label">Open Positions</div><div id="positions"></div></section>
<nav class="nav"><span class="active">⌂ Home</span><span>◉ Markets</span><span>▣ Positions</span><span>↗ History</span><span>✦ ATLAS</span><span>⚙ Settings</span></nav>
<div class="footer">Demo / paper environment · Auto-refresh 2s · Last update: <span id="updated">—</span></div>
</main>
<script>
const money=n=>'$'+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const cls=n=>Number(n)>=0?'green':'red';
async function refresh(){try{const r=await fetch('/dashboard/state',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();const e=d.equity||{};document.getElementById('status').textContent='LIVE';document.getElementById('equity').textContent=money(e.equity);const p=Number(e.unrealized_pnl||0);document.getElementById('pnl').textContent=(p>=0?'+':'')+money(p);document.getElementById('pnl').className='value '+cls(p);document.getElementById('today').textContent='Balance '+money(e.balance);document.getElementById('count').textContent=String(e.open_positions||0);document.getElementById('risk').textContent=d.risk?.level||'LOW';document.getElementById('riskPct').textContent=Number(d.risk?.daily_risk_percent||0).toFixed(1)+'%';document.getElementById('decision').textContent=d.atlas?.decision||'WAIT';document.getElementById('strength').textContent=d.atlas?.strength||'Monitoring market conditions';document.getElementById('alignment').textContent=d.atlas?.alignment||'No active alignment';document.getElementById('markets').innerHTML=Object.entries(d.prices||{}).map(([s,p])=>`<div class="row"><b>${s}</b><span>${money(p)}</span><span class="pill">LIVE</span><span class="muted">${new Date().toLocaleTimeString()}</span></div>`).join('');document.getElementById('positions').innerHTML=(e.positions||[]).length?(e.positions||[]).map(p=>`<div class="row"><div><b>${p.symbol}</b><div class="muted">${p.direction}</div></div><span>Entry ${money(p.entry)}</span><span>Now ${money(p.current_price)}</span><b class="${cls(p.unrealized_pnl)}">${p.unrealized_pnl>=0?'+':''}${money(p.unrealized_pnl)}</b></div>`).join(''):'<div class="empty">No open positions. The account is clear.</div>';document.getElementById('updated').textContent=new Date().toLocaleTimeString()}catch(err){document.getElementById('status').textContent='OFFLINE';document.getElementById('updated').textContent=err.message}}
refresh();setInterval(refresh,2000);
</script></body></html>"""
