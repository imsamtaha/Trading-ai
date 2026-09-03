from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles, get_price
from app.intelligence.scoring import (
    create_atlas_trade_candidate,
    score_analysis,
)
from app.paper_trading.engine import PersistentPaperTradingEngine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ACCOUNT_ID = 3
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ATLAS_DEMO_SYMBOLS = ["XAUUSD", "SILVER", "GAS", "EURUSD", "SOLUSDT", "XRPUSDT"]


def _direction_score(label: str | None) -> float:
    normalized = (label or "").strip().lower()
    if normalized == "bullish":
        return 0.7
    if normalized == "bearish":
        return -0.7
    return 0.0


def _momentum_score(label: str | None) -> float:
    normalized = (label or "").strip().lower()
    if normalized == "bullish":
        return 0.5
    if normalized == "bearish":
        return -0.5
    return 0.0


def _volatility_score(technical: dict) -> float:
    price = technical.get("price")
    atr = (technical.get("indicators") or {}).get("atr_14")
    if not price or not atr:
        return 0.0
    return min(1.0, abs(float(atr) / float(price)) * 50.0)


def _demo_regime_from_technical(technical: dict) -> dict:
    trend = technical.get("trend")
    trend_score = _direction_score(trend)
    volatility = _volatility_score(technical)

    if volatility >= 0.75:
        primary = "HIGH_VOLATILITY"
    elif trend == "bullish":
        primary = "BULL_TREND"
    elif trend == "bearish":
        primary = "BEAR_TREND"
    else:
        primary = "RANGE"

    return {
        "primary_regime": primary,
        "regime_score": trend_score,
        "trend": primary if primary in {"BULL_TREND", "BEAR_TREND"} else "RANGE",
        "volatility": "HIGH_VOLATILITY" if volatility >= 0.75 else "NORMAL_VOLATILITY",
        "risk": "NEUTRAL_RISK",
        "event_risk": "NORMAL_EVENT_RISK",
        "raw_state": {
            "trend_score": trend_score,
            "volatility_score": volatility,
            "momentum_score": _momentum_score(technical.get("momentum")),
            "volume_score": 0.5 if technical.get("volume_state") == "high" else 0.0,
            "event_risk_score": 0.0,
            "risk_sentiment_score": 0.0,
        },
    }


def _analyze_demo_symbol(symbol: str, interval: str, account_balance: float) -> dict:
    market_data = get_candles(symbol, interval, 120)
    candles = market_data["candles"]
    technical = analyze_candles(candles)
    structure = analyze_structure(candles)
    regime = _demo_regime_from_technical(technical)

    decision = score_analysis(
        asset=symbol,
        timeframe=interval,
        technical_analysis=technical,
        structure_analysis=structure,
        regime_analysis=regime,
        risk_reward=2.0,
        account_risk_fraction=0.01,
    )
    candidate = create_atlas_trade_candidate(
        decision=decision,
        technical=technical,
        account_balance=account_balance,
        risk_percent=1.0,
    )

    return {
        "symbol": symbol,
        "interval": interval,
        "status": candidate.get("status", "NO_TRADE"),
        "price": technical.get("price"),
        "trend": technical.get("trend"),
        "momentum": technical.get("momentum"),
        "structure": structure.get("structure"),
        "regime": regime.get("primary_regime"),
        "atlas_decision": decision.to_dict(),
        "trade_candidate": candidate,
    }


@router.get("/state")
def dashboard_state(account_id: int = ACCOUNT_ID):
    try:
        engine = PersistentPaperTradingEngine(account_id)
        account = engine.account()
        positions = engine.positions()

        prices = {}
        price_errors = {}
        for symbol in SYMBOLS:
            try:
                data = get_price(symbol)
                prices[symbol] = float(data["price"])
            except Exception as exc:
                price_errors[symbol] = str(exc)

        equity = engine.calculate_equity(prices)

        return {
            "status": "LIVE",
            "mode": "paper_trading",
            "account": account,
            "prices": prices,
            "price_errors": price_errors,
            "equity": equity,
            "positions": positions,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/demo-state")
def atlas_demo_state(
    interval: str = "1h",
    account_balance: float = 10_000.0,
):
    results = []
    for symbol in ATLAS_DEMO_SYMBOLS:
        try:
            results.append(_analyze_demo_symbol(symbol, interval, account_balance))
        except Exception as exc:
            results.append({
                "symbol": symbol,
                "interval": interval,
                "status": "ERROR",
                "error": str(exc),
            })

    trade_candidates = [
        item for item in results
        if item.get("status") == "TRADE_CANDIDATE"
    ]
    no_trades = [
        item for item in results
        if item.get("status") == "NO_TRADE"
    ]
    errors = [
        item for item in results
        if item.get("status") == "ERROR"
    ]

    return {
        "status": "DEMO_READY",
        "mode": "live_market_data_paper_trading_demo",
        "execution": "disabled",
        "interval": interval,
        "symbols": ATLAS_DEMO_SYMBOLS,
        "summary": {
            "analyzed": len(results),
            "trade_candidates": len(trade_candidates),
            "no_trades": len(no_trades),
            "errors": len(errors),
        },
        "results": results,
    }


@router.get("", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS Trading AI — Demo Cockpit</title>
<style>
:root{color-scheme:dark;--bg:#060914;--card:#0f1626;--card2:#111b2f;--line:#24304a;--text:#eef2ff;--muted:#8995b0;--green:#35d07f;--red:#ff6575;--amber:#f59e0b;--blue:#6ea8fe;--violet:#a78bfa}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top left,#18233c,#060914 45%);color:var(--text);font:14px system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1360px;margin:auto;padding:24px}.head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.brand{font-size:28px;font-weight:900;letter-spacing:.02em}.subtitle{color:var(--muted);margin-top:4px}.live{display:flex;align-items:center;gap:8px;color:var(--green);font-weight:800}.dot{width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 18px var(--green)}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(4,1fr)}.two{grid-template-columns:1.1fr .9fr}.three{grid-template-columns:repeat(3,1fr)}.card{background:linear-gradient(180deg,var(--card),#0b1221);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 14px 50px rgba(0,0,0,.22)}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.big{font-size:25px;font-weight:850;margin-top:6px}.green{color:var(--green)}.red{color:var(--red)}.amber{color:var(--amber)}.blue{color:var(--blue)}.violet{color:var(--violet)}.row{display:grid;grid-template-columns:1.2fr 1fr 1fr 1fr;gap:10px;padding:12px 0;border-bottom:1px solid var(--line);align-items:center}.row:last-child{border-bottom:0}.atlasRow{grid-template-columns:1fr .8fr .8fr .8fr .9fr .9fr}.muted{color:var(--muted);font-size:12px}.tag{border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:11px;display:inline-block}.tag.green{border-color:rgba(53,208,127,.4);background:rgba(53,208,127,.08)}.tag.amber{border-color:rgba(245,158,11,.5);background:rgba(245,158,11,.08)}.tag.red{border-color:rgba(255,101,117,.4);background:rgba(255,101,117,.08)}.empty{color:var(--muted);padding:18px 0}.err{color:var(--red)}button{background:linear-gradient(135deg,#f59e0b,#fb923c);color:#111827;border:0;border-radius:999px;padding:10px 14px;font-weight:850;cursor:pointer}.pillbar{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.small{font-size:12px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}@media(max-width:900px){main{padding:14px}.stats,.three,.two{grid-template-columns:1fr}.row,.atlasRow{grid-template-columns:1fr 1fr}.brand{font-size:22px}}
</style></head>
<body><main>
<div class="head"><div><div class="brand">ATLAS ULTIMATE TRADING AI HUB</div><div class="subtitle">Real market-data demo · deterministic scoring · risk-gated paper candidates</div></div><div class="live"><span class="dot"></span><span id="status">CONNECTING</span></div></div>
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
<section class="card" style="margin-top:12px"><div style="display:flex;justify-content:space-between;gap:12px;align-items:center"><div><div class="label">ATLAS Real Demo</div><div class="muted">Live data analysis only. Execution disabled. Paper candidate boundary active.</div></div><button onclick="refreshDemo()">Run ATLAS Demo</button></div><div class="grid three" style="margin-top:12px"><div><div class="label">Analyzed</div><div class="big" id="demoAnalyzed">—</div></div><div><div class="label">Candidates</div><div class="big green" id="demoCandidates">—</div></div><div><div class="label">No Trade / Errors</div><div class="big amber" id="demoNoTrade">—</div></div></div><div id="atlasDemo" style="margin-top:12px"></div></section>
<section class="card" style="margin-top:12px"><div class="label">Open Positions</div><div id="positions"></div></section>
<div class="muted" style="margin-top:10px">Auto-refresh: 2 seconds · ATLAS demo refresh: manual + 30 seconds · Last update: <span id="updated">—</span></div>
</main>
<script>
const money=n=>'$'+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const cls=n=>Number(n)>=0?'green':'red';
function tag(status){if(status==='TRADE_CANDIDATE')return '<span class="tag green">READY</span>';if(status==='ERROR')return '<span class="tag red">ERROR</span>';return '<span class="tag amber">NO TRADE</span>'}
async function refresh(){try{const r=await fetch('/dashboard/state',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();const e=d.equity;document.getElementById('status').textContent='LIVE';document.getElementById('equity').textContent=money(e.equity);document.getElementById('balance').textContent=money(e.balance);const p=document.getElementById('pnl');p.textContent=(e.unrealized_pnl>=0?'+':'')+money(e.unrealized_pnl);p.className='big '+cls(e.unrealized_pnl);document.getElementById('exposure').textContent=money(e.exposure);const marketRows=Object.entries(d.prices).map(([s,p])=>`<div class="row"><b>${s}</b><span>${money(p)}</span><span class="tag green">LIVE</span><span class="muted">${new Date().toLocaleTimeString()}</span></div>`).join('');const errors=Object.entries(d.price_errors||{}).map(([s,msg])=>`<div class="row"><b>${s}</b><span class="err">ERROR</span><span></span><span class="muted">${msg}</span></div>`).join('');document.getElementById('markets').innerHTML=marketRows+errors;document.getElementById('positions').innerHTML=e.positions.length?e.positions.map(p=>`<div class="row"><div><b>${p.symbol}</b><div class="muted">${p.direction}</div></div><span>Entry ${money(p.entry)}</span><span>Now ${money(p.current_price)}</span><b class="${cls(p.unrealized_pnl)}">${p.unrealized_pnl>=0?'+':''}${money(p.unrealized_pnl)}</b></div>`).join(''):'<div class="empty">No open positions.</div>';document.getElementById('system').innerHTML=`<div class="row"><span>Mode</span><b>${d.mode}</b></div><div class="row"><span>Positions</span><b>${e.open_positions}</b></div><div class="row"><span>Account</span><b>#${d.account.id}</b></div><div class="row"><span>Execution</span><b class="amber">DISABLED</b></div>`;document.getElementById('updated').textContent=new Date().toLocaleTimeString()}catch(err){document.getElementById('status').textContent='OFFLINE';document.getElementById('system').innerHTML='<div class="err">Dashboard API unavailable: '+err.message+'</div>'}}
async function refreshDemo(){const box=document.getElementById('atlasDemo');box.innerHTML='<div class="empty">Running ATLAS demo analysis...</div>';try{const r=await fetch('/dashboard/demo-state?interval=1h',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();document.getElementById('demoAnalyzed').textContent=d.summary.analyzed;document.getElementById('demoCandidates').textContent=d.summary.trade_candidates;document.getElementById('demoNoTrade').textContent=(d.summary.no_trades+d.summary.errors);box.innerHTML=d.results.map(x=>{const dec=x.atlas_decision||{};const tc=x.trade_candidate||{};const risk=(tc.risk||{});const reason=x.error||tc.reason||((dec.veto_reasons||[]).join(', ')||'—');return `<div class="row atlasRow"><div><b>${x.symbol}</b><div class="muted">${x.interval} · ${x.regime||'—'}</div></div><span>${x.price?money(x.price):'—'}</span><span>${x.trend||'—'} / ${x.structure||'—'}</span><span>${tag(x.status)}</span><span class="mono">L:${dec.long_score??'—'} S:${dec.short_score??'—'}</span><span class="muted">${x.status==='TRADE_CANDIDATE'?'R:R '+(risk.risk_reward??'—'):reason}</span></div>`}).join('')}catch(err){box.innerHTML='<div class="err">ATLAS demo unavailable: '+err.message+'</div>'}}
refresh();refreshDemo();setInterval(refresh,2000);setInterval(refreshDemo,30000);
</script></body></html>"""
