from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.analysis.structure import analyze_structure
from app.analysis.technical import analyze_candles
from app.data.market import get_candles, get_price
from app.intelligence.scoring import create_atlas_trade_candidate, score_analysis
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
        prices: dict[str, float] = {}
        price_errors: dict[str, str] = {}

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
            "positions": engine.positions(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/demo-state")
def atlas_demo_state(interval: str = "1h", account_balance: float = 10_000.0):
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

    return {
        "status": "DEMO_READY",
        "mode": "live_market_data_paper_trading_demo",
        "execution": "disabled",
        "interval": interval,
        "symbols": ATLAS_DEMO_SYMBOLS,
        "summary": {
            "analyzed": len(results),
            "trade_candidates": sum(item.get("status") == "TRADE_CANDIDATE" for item in results),
            "no_trades": sum(item.get("status") == "NO_TRADE" for item in results),
            "errors": sum(item.get("status") == "ERROR" for item in results),
        },
        "results": results,
    }


@router.get("/mt5-state")
def mt5_state():
    """Expose FxPro/MT5 telemetry through a hard read-only dashboard boundary."""
    try:
        from app.dashboard.api import atlas_dashboard_state

        state = atlas_dashboard_state()
        state["mode"] = "READ_ONLY"
        state["execution"] = "disabled"
        services = dict(state.get("services") or {})
        services["execution_gate"] = "DISABLED"
        services["subscriber_access"] = "READ_ONLY"
        state["services"] = services
        return state
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MT5 read-only dashboard unavailable: {exc}")


@router.get("", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS Ultimate Trading AI Hub</title>
<style>
:root{color-scheme:dark;--bg:#080a0f;--card:#10151e;--line:#273345;--text:#f4f6fa;--muted:#91a0b5;--orange:#ff8a24;--green:#39d98a;--red:#ff6174;--blue:#72a7ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% 0,#1a2638,#080a0f 44%);color:var(--text);font:14px system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1500px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:16px}.title{font-size:26px;font-weight:900}.sub{color:var(--muted);font-size:12px}.badge{padding:8px 11px;border:1px solid var(--line);border-radius:999px}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(6,1fr)}.split{grid-template-columns:1.2fr .8fr}.card{background:linear-gradient(180deg,#111925,#0c121b);border:1px solid var(--line);border-radius:16px;padding:16px}.label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.1em}.big{font-size:23px;font-weight:900;margin-top:6px}.orange{color:var(--orange)}.green{color:var(--green)}.red{color:var(--red)}.blue{color:var(--blue)}.row{display:grid;grid-template-columns:1.2fr .9fr .9fr .9fr .9fr;gap:8px;padding:10px 0;border-bottom:1px solid var(--line)}.row:last-child{border-bottom:0}.muted{color:var(--muted);font-size:12px}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px}.err{color:var(--red)}@media(max-width:950px){.stats,.split{grid-template-columns:1fr 1fr}.row{grid-template-columns:1fr 1fr}}@media(max-width:600px){.stats,.split{grid-template-columns:1fr}}
</style>
</head>
<body><main>
<div class="top"><div><div class="title">ATLAS ULTIMATE TRADING AI HUB</div><div class="sub">FxPro MT5 read-only cockpit · ATLAS scoring · paper/demo validation</div></div><div class="badge"><span id="systemStatus">CONNECTING</span></div></div>
<div class="grid stats">
<div class="card"><div class="label">MT5</div><div class="big" id="mt5">—</div></div>
<div class="card"><div class="label">Account</div><div class="big" id="account">—</div></div>
<div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div>
<div class="card"><div class="label">Equity</div><div class="big" id="equity">—</div></div>
<div class="card"><div class="label">Open Positions</div><div class="big" id="positionsCount">—</div></div>
<div class="card"><div class="label">Execution</div><div class="big red">DISABLED</div></div>
</div>
<div class="grid split" style="margin-top:12px">
<section class="card"><div class="label">MT5 / FxPro Symbols</div><div id="symbols"><div class="muted">Loading broker telemetry…</div></div></section>
<section class="card"><div class="label">Broker Account</div><div id="broker"><div class="muted">Loading account…</div></div></section>
</div>
<div class="grid split" style="margin-top:12px">
<section class="card"><div class="label">ATLAS Demo Decisions</div><div id="demo"><div class="muted">Loading demo analysis…</div></div></section>
<section class="card"><div class="label">MT5 Positions</div><div id="mt5positions"><div class="muted">Loading positions…</div></div></section>
</div>
<div class="muted" style="margin-top:10px">Read-only broker telemetry. Real order execution is disabled.</div>
</main>
<script>
const money=n=>n==null?'—':'$'+Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const safe=v=>v==null?'—':String(v);
async function getJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok){let detail='HTTP '+r.status;try{const j=await r.json();detail=j.detail||detail}catch{}throw new Error(detail)}return r.json()}
async function refreshMT5(){try{const d=await getJson('/dashboard/mt5-state');document.getElementById('systemStatus').textContent='ONLINE · READ ONLY';document.getElementById('mt5').textContent=d.services?.mt5||'ONLINE';document.getElementById('mt5').className='big green';document.getElementById('account').textContent=d.account?.account_type||'—';document.getElementById('balance').textContent=money(d.account?.balance);document.getElementById('equity').textContent=money(d.account?.equity);document.getElementById('positionsCount').textContent=d.open_positions??0;document.getElementById('broker').innerHTML=`<div class="row"><span>Server</span><b>${safe(d.account?.server)}</b></div><div class="row"><span>Login</span><b>${safe(d.account?.login)}</b></div><div class="row"><span>Currency</span><b>${safe(d.account?.currency)}</b></div><div class="row"><span>Trade allowed</span><b>${safe(d.account?.trade_allowed)}</b></div><div class="row"><span>Execution gate</span><b class="red">DISABLED</b></div>`;document.getElementById('symbols').innerHTML=(d.symbols||[]).slice(0,12).map(x=>`<div class="row"><b>${safe(x.canonical_symbol||x.symbol)}</b><span>${safe(x.price)}</span><span>${safe(x.decision?.decision)}</span><span>score ${safe(x.decision?.score)}</span><span>${safe(x.quality?.signal_quality)}</span></div>`).join('')||'<div class="muted">No broker symbols returned.</div>';document.getElementById('mt5positions').innerHTML=(d.positions||[]).map(p=>`<div class="row"><b>${safe(p.symbol)}</b><span>${safe(p.direction)}</span><span>${safe(p.volume)}</span><span>${safe(p.price_open)}</span><span>${money(p.profit)}</span></div>`).join('')||'<div class="muted">No MT5 positions.</div>'}catch(e){document.getElementById('systemStatus').textContent='MT5 OFFLINE';document.getElementById('mt5').textContent='OFFLINE';document.getElementById('mt5').className='big red';document.getElementById('broker').innerHTML='<div class="err">'+e.message+'</div>'}}
async function refreshDemo(){try{const d=await getJson('/dashboard/demo-state');document.getElementById('demo').innerHTML=(d.results||[]).map(x=>`<div class="row"><b>${safe(x.symbol)}</b><span>${safe(x.status)}</span><span>${safe(x.trend)}</span><span>${safe(x.regime)}</span><span>${safe(x.atlas_decision?.bias||x.atlas_decision?.status)}</span></div>`).join('')}catch(e){document.getElementById('demo').innerHTML='<div class="err">'+e.message+'</div>'}}
refreshMT5();refreshDemo();setInterval(refreshMT5,5000);setInterval(refreshDemo,15000);
</script>
</body></html>'''
