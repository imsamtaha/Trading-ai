import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dashboard.api import router as api_router
from app.dashboard.agent_panel import router as agent_panel_router
from app.dashboard.account_panel import ACCOUNT_PANEL
from app.dashboard.demo_panel import router as demo_panel_router
from app.dashboard.fxpro_onboarding import fxpro_entry_card, router as fxpro_onboarding_router
from app.dashboard.setups_panel import router as setups_panel_router
from app.dashboard.trading_hub import enhance_atlas_html
from app.dashboard.views import DASHBOARD_HTML
from app.execution.provider_mode import ctrader_selected

router = APIRouter()
CANONICAL_ATLAS_PATH = "/"
LEGACY_ATLAS_PATH = "/atlas-ultimate"


def _stripe_link(plan: str) -> str | None:
    value = os.getenv(f"ATLAS_STRIPE_LINK_{plan.upper()}", "").strip()
    return value if value.startswith("https://buy.stripe.com/") else None


def _stripe_button(plan: str) -> str:
    link = _stripe_link(plan)
    if link:
        return f'<a class="btn atlas-3d" href="{link}" target="_blank" rel="noopener">Pay with Stripe</a>'
    return '<span class="btn ghost atlas-3d" aria-disabled="true" title="Stripe checkout becomes available after account verification">Stripe activation pending</span>'


def _atlas_ultimate_html() -> str:
    starter_stripe = _stripe_button("watch")
    pro_stripe = _stripe_button("reader")
    elite_stripe = _stripe_button("pro")
    if ctrader_selected():
        broker_entry = (
            '<section class="card" id="broker-connection">'
            '<h2>cTrader Demo</h2><p>View the demo account and PAPER evidence in the owner workspace.</p>'
            '<a class="btn ghost atlas-3d" href="/sam">Owner workspace</a></section>'
        )
    else:
        broker_entry = fxpro_entry_card()
    plans = f'''
<section id="plans" class="card atlas-plans" style="margin-top:18px">
  <div class="label">ATLAS ULTIMATE ACCESS</div>
  <h2 style="font-size:clamp(28px,4vw,48px);margin:8px 0 6px">Choose your intelligence level.</h2>
  <p class="mini" style="max-width:820px;font-size:13px;line-height:1.6">Choose a paid ATLAS intelligence plan for customer access. Whish Pay and available card checkout are subscription payment methods only; FxPro account funding remains separate. There is no free customer tier.</p>
  <div class="plans-grid">
    <div class="card plan-card"><div class="label">ATLAS Starter</div><div class="big">$99<span class="mini"> / month</span></div><p class="mini">Live market intelligence · AI chart workspace · Editable indicators · Setup context · ATLAS AI question assistant.</p>{starter_stripe}<a class="btn ghost atlas-3d" href="/billing/whish/watch">Pay with Whish Pay</a></div>
    <div class="card plan-card" style="border-color:#ff7a1a66"><div class="label">ATLAS Pro</div><div class="big">$149<span class="mini"> / month</span></div><p class="mini">Everything in Starter · Live setup and signal overlays · Entry/reference zones · Targets · Stop/invalidation levels · Risk and confidence context.</p>{pro_stripe}<a class="btn ghost atlas-3d" href="/billing/whish/reader">Pay with Whish Pay</a></div>
    <div class="card plan-card"><div class="label">ATLAS Elite</div><div class="big">$299<span class="mini"> / month</span></div><p class="mini">Everything in Pro · Advanced multi-asset analysis · Risk/position monitoring · Exit and stop alerts · Priority intelligence · Advanced AI chart and assistant features.</p>{elite_stripe}<a class="btn ghost atlas-3d" href="/billing/whish/pro">Pay with Whish Pay</a></div>
    <div class="card plan-card"><div class="label">Enterprise</div><div class="big">Custom</div><p class="mini">Manual application and review · Team access · Custom integrations and deployment planning · Commercial quote based on required services.</p><a class="btn ghost atlas-3d" href="mailto:info@justai-atlas.online?subject=ATLAS%20ULTIMATE%20Enterprise%20Application">Apply / Contact CEO</a></div>
  </div>
  <div class="notice">ATLAS subscription billing is separate from FxPro. Trading funds are never collected by this checkout. The customer workspace is analysis/demo oriented; real-money trading remains off in the public dashboard and outcomes are not guaranteed.</div>
</section>
<style>
.plans-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}}.plan-card{{display:flex;flex-direction:column;gap:12px;position:relative;overflow:hidden}}.plan-card:before{{content:"";position:absolute;inset:-80% 45% auto -30%;height:220px;background:radial-gradient(circle,#ff7a1a1f,transparent 68%);pointer-events:none}}.atlas-tech-bg{{position:fixed;inset:0;z-index:-1;pointer-events:none;perspective:900px;overflow:hidden}}.atlas-tech-bg:before{{content:"";position:absolute;left:-15%;right:-15%;bottom:-36%;height:72%;transform:rotateX(64deg);transform-origin:center top;background-image:linear-gradient(#ff7a1a14 1px,transparent 1px),linear-gradient(90deg,#91a4bd12 1px,transparent 1px);background-size:58px 58px}}.atlas-tech-bg:after{{content:"";position:absolute;width:560px;height:560px;right:-180px;top:20%;border:1px solid #ff7a1a20;border-radius:50%;box-shadow:0 0 80px #ff7a1a12,inset 0 0 80px #91a4bd0b}}@media(max-width:1180px){{.plans-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:700px){{.plans-grid{{grid-template-columns:1fr}}}}
</style>
'''
    scripts = '<script src="/ui/preferences.js"></script><script src="/ui/agent-panel.js"></script><script src="/ui/demo-panel.js"></script><script src="/ui/setups-panel.js"></script><script src="/assets/google-auth.js" defer></script>'
    html = DASHBOARD_HTML.replace('href="/subscribe"', 'href="#plans"')
    insert = ACCOUNT_PANEL + broker_entry + plans
    html = html.replace('</main>', insert + '</main>') if '</main>' in html else html.replace('<div class="notice" id="disclaimer">', insert + '<div class="notice" id="disclaimer">')
    html = html.replace('</body>', scripts + '</body>')
    return enhance_atlas_html(html)


def atlas_ultimate_view() -> HTMLResponse:
    """Compatibility callable used by tests and internal integrations."""
    return HTMLResponse(_atlas_ultimate_html())


@router.get(LEGACY_ATLAS_PATH, include_in_schema=False)
def legacy_atlas_redirect() -> RedirectResponse:
    return RedirectResponse(url=CANONICAL_ATLAS_PATH, status_code=308)


@router.get("/dashboard", include_in_schema=False)
def legacy_dashboard_redirect() -> RedirectResponse:
    return RedirectResponse(url=CANONICAL_ATLAS_PATH, status_code=308)


router.include_router(api_router)
router.include_router(agent_panel_router)
router.include_router(demo_panel_router)
router.include_router(setups_panel_router)
router.include_router(fxpro_onboarding_router)

__all__ = ["router", "mt5_state", "CANONICAL_ATLAS_PATH", "LEGACY_ATLAS_PATH"]

ATLAS_DEMO_SYMBOLS = ["XAUUSD", "GAS", "XAGUSD", "EURUSD", "XRPUSDT", "SOLUSDT"]


@router.get("/dashboard/mt5-state")
def mt5_state():
    """Expose MT5 dashboard telemetry as a live demo workspace."""
    from app.dashboard import api as dashboard_api
    state = dashboard_api.atlas_dashboard_state()
    live_demo = os.getenv("ATLAS_LIVE_DEMO", "false").lower() == "true"
    state["mode"] = "LIVE_DEMO" if live_demo else "READ_ONLY"
    state["execution"] = "simulated_demo" if live_demo else "disabled"
    services = dict(state.get("services") or {})
    services["execution_gate"] = "DEMO_SIMULATED" if live_demo else "DISABLED"
    services["subscriber_access"] = "LIVE_DEMO" if live_demo else "READ_ONLY"
    state["services"] = services
    return state


def _demo_regime_from_technical(technical):
    from app.intelligence.regime.engine import MarketRegimeEngine, MarketState
    direction = {"bullish": 0.8, "bearish": -0.8}
    price = float(technical.get("price") or 0)
    atr = float((technical.get("indicators") or {}).get("atr_14") or 0)
    state = MarketState(trend_score=direction.get(str(technical.get("trend", "")).lower(), 0.0), momentum_score=direction.get(str(technical.get("momentum", "")).lower(), 0.0), volatility_score=min(1.0, max(0.0, atr / price * 10)) if price > 0 else 0.0, volume_score={"high": 0.8, "normal": 0.0, "low": -0.5}.get(str(technical.get("volume_state", "")).lower(), 0.0), event_risk_score=0.0, risk_sentiment_score=0.0)
    result = MarketRegimeEngine().analyze(state)
    result["context_limitations"] = ["News and risk sentiment are not evaluated."]
    return result


def _analyze_demo_symbol(symbol, interval, account_balance):
    from app.data.market import get_candles
    from app.analysis.technical import analyze_candles
    from app.analysis.structure import analyze_structure
    from app.strategies.signal import generate_signal
    from app.strategies.trade import create_trade_candidate
    market = get_candles(symbol, interval, 120)
    technical = analyze_candles(market["candles"])
    structure = analyze_structure(market["candles"])
    signal = generate_signal(technical, structure)
    candidate = create_trade_candidate(signal, technical, account_balance)
    return {"symbol": symbol, "interval": interval, "status": candidate["status"], "technical": technical, "structure": structure, "regime": _demo_regime_from_technical(technical), "signal": signal, "trade_candidate": candidate, "execution": "disabled", "data_source": "Public market provider; commodity prices may be futures proxies."}


def atlas_demo_state(interval="15m", account_balance=10000.0):
    import math
    if interval not in {"5m", "15m", "30m", "1h"}: raise ValueError("Unsupported demo interval")
    if not math.isfinite(account_balance) or account_balance <= 0: raise ValueError("Account balance must be positive and finite")
    results = []
    for symbol in ATLAS_DEMO_SYMBOLS:
        try: results.append(_analyze_demo_symbol(symbol, interval, account_balance))
        except Exception: results.append({"symbol": symbol, "interval": interval, "status": "ERROR", "error": "Market analysis unavailable"})
    errors = sum(item["status"] == "ERROR" for item in results)
    return {"status": "DEMO_READY" if errors < len(results) else "DEMO_UNAVAILABLE", "execution": "disabled", "results": results, "summary": {"analyzed": len(results), "no_trades": sum(item["status"] == "NO_TRADE" for item in results), "errors": errors}, "disclaimer": "Read-only analysis, not executed demo trades or verified performance."}
