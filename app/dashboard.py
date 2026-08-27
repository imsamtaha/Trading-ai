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
<title>Trading AI — Live Monitor</title>
<style>
:root{color-scheme:dark;--bg:#070b14;--card:#0f1626;--line:#24304a;--text:#eef2ff;--muted:#8995b0;--green:#35d07f;--red:#ff6575;--amber:#f59e0b;--blue:#6ea8fe}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1280px;margin:auto;padding:24px}.head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.brand{font-size:24px;font-weight:800}.live{display:flex;align-items:center;gap:8px;color:var(--green);font-weight:700}.dot{width:9px;height:9px;border-radius:50%;background:var(--green)}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(4,1fr)}.two{grid-template-columns:1.3fr .9fr}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.big{font-size:25px;font-weight:800;margin-top:6px}.green{color:var(--green)}.red{color:var(--red)}.amber{color:var(--amber)}.row{display:grid;grid-template-columns:1.2fr 1fr 1fr 1fr;gap:10px;padding:12px 0;border-bottom:1px solid var(--line);align-items:center}.row:last-child{border-bottom:0}.muted{color:var(--muted);font-size:12px}.tag{border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:11px;display:inline-block}.empty{color:var(--muted);padding:18px 0}.err{color:var(--red)}@media(max-width:800px){main{padding:14px}.stats{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}.row{grid-template-columns:1fr 1fr}.row>*:nth-child(n+3){text-align:right}.brand{font-size:20px}}
</style></head>
<body><main>
<div class="head"><div><div class="brand">TRADING AI</div><div class="muted">Live Trader Monitor · Paper Trading</div></div><div class="live"><span class="dot"></span><span id="status">CONNECTING</span></div></div>
<div class="grid stats">
<div class="card"><div class="label">Equity</div><div class="big" id="equity">—</div></div>
<div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div>
<div class="card"><div class="label">Unrealized P&amp;L</div><div class="big" id="pnl">—</div></div>
<div class="card"><div class="label">Exposure</div><div class="big" id="exposure">—</div></div>
</div>
<div class="grid two" style="margin-top:12px">
<section class="card"><div class="label">Market Movement</div><div id="markets"></div></section>
<section class="card"><div class="label">System</div><div style="margin-top:12px" id="system"></div></section>
</div>
<section class="card" style="margin-top:12px"><div class="label">Open Positions</div><div id="positions"></div></section>
<div class="muted" style="margin-top:10px">Auto-refresh: 2 seconds · Last update: <span id="updated">—</span></div>
</main>
<script>
const money=n=>'$'+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const cls=n=>Number(n)>=0?'green':'red';
async function refresh(){try{const r=await fetch('/dashboard/state',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();const e=d.equity;document.getElementById('status').textContent='LIVE';document.getElementById('equity').textContent=money(e.equity);document.getElementById('balance').textContent=money(e.balance);const p=document.getElementById('pnl');p.textContent=(e.unrealized_pnl>=0?'+':'')+money(e.unrealized_pnl);p.className='big '+cls(e.unrealized_pnl);document.getElementById('exposure').textContent=money(e.exposure);document.getElementById('markets').innerHTML=Object.entries(d.prices).map(([s,p])=>`<div class="row"><b>${s}</b><span>${money(p)}</span><span class="tag">LIVE</span><span class="muted">${new Date().toLocaleTimeString()}</span></div>`).join('');document.getElementById('positions').innerHTML=e.positions.length?e.positions.map(p=>`<div class="row"><div><b>${p.symbol}</b><div class="muted">${p.direction}</div></div><span>Entry ${money(p.entry)}</span><span>Now ${money(p.current_price)}</span><b class="${cls(p.unrealized_pnl)}">${p.unrealized_pnl>=0?'+':''}${money(p.unrealized_pnl)}</b></div>`).join(''):'<div class="empty">No open positions.</div>';document.getElementById('system').innerHTML=`<div class="row"><span>Mode</span><b>${d.mode}</b></div><div class="row"><span>Positions</span><b>${e.open_positions}</b></div><div class="row"><span>Account</span><b>#${d.account.id}</b></div>`;document.getElementById('updated').textContent=new Date().toLocaleTimeString()}catch(err){document.getElementById('status').textContent='OFFLINE';document.getElementById('system').innerHTML='<div class="err">Dashboard API unavailable: '+err.message+'</div>'}}
refresh();setInterval(refresh,2000);
</script></body></html>"""
