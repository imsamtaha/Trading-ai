import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dashboard.api import router as api_router
from app.dashboard.agent_panel import router as agent_panel_router
from app.dashboard.demo_panel import router as demo_panel_router
from app.dashboard.views import DASHBOARD_HTML

router = APIRouter()
CANONICAL_ATLAS_PATH = "/atlas-ultimate"


def _stripe_link(plan: str) -> str | None:
    value = os.getenv(f"ATLAS_STRIPE_LINK_{plan.upper()}", "").strip()
    return value if value.startswith("https://buy.stripe.com/") else None


def _stripe_button(plan: str) -> str:
    link = _stripe_link(plan)
    if link:
        return f'<a class="btn" href="{link}" target="_blank" rel="noopener">Pay with Stripe</a>'
    return '<span class="btn ghost" aria-disabled="true" title="Complete Stripe account verification to activate live card payments">Stripe activation pending</span>'


def _atlas_ultimate_html() -> str:
    reader_stripe = _stripe_button("reader")
    pro_stripe = _stripe_button("pro")
    plans = f'''
<section id="plans" class="card" style="margin-top:18px">
  <div class="label">ATLAS ULTIMATE ACCESS</div>
  <h2 style="font-size:clamp(28px,4vw,48px);margin:8px 0 6px">Choose your intelligence level.</h2>
  <p class="mini" style="max-width:760px;font-size:13px;line-height:1.6">Start free, then upgrade when you need deeper read-only market intelligence. Stripe card checkout becomes available automatically when the live Stripe account is fully verified. Whish Money remains available through manual review.</p>
  <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px" class="plans-grid">
    <div class="card" style="box-shadow:none;display:flex;flex-direction:column;gap:12px">
      <div class="label">Free Demo</div><div class="big">$0</div>
      <p class="mini">Explore ATLAS ULTIMATE interface, synthetic scenarios and educational market context.</p>
      <a class="btn ghost" href="#markets">Explore free</a>
    </div>
    <div class="card" style="box-shadow:none;display:flex;flex-direction:column;gap:12px">
      <div class="label">Reader</div><div class="big">$49<span class="mini"> / month</span></div>
      <p class="mini">3-day free trial · Read-only MT5 telemetry · Wall Street board · Financial news.</p>
      {reader_stripe}
      <a class="btn ghost" href="/billing/whish/reader">Whish Money</a>
    </div>
    <div class="card" style="box-shadow:none;display:flex;flex-direction:column;gap:12px;border-color:#ff7a1a66">
      <div class="label">Pro Reader · Popular</div><div class="big">$99<span class="mini"> / month</span></div>
      <p class="mini">3-day free trial · Expanded multi-asset opportunity matrix · Advanced risk reports · Priority briefings.</p>
      {pro_stripe}
      <a class="btn ghost" href="/billing/whish/pro">Whish Money</a>
    </div>
    <div class="card" style="box-shadow:none;display:flex;flex-direction:column;gap:12px">
      <div class="label">Enterprise</div><div class="big">Custom</div>
      <p class="mini">Team access, custom integrations and deployment planning. Pricing is quoted separately.</p>
      <a class="btn ghost" href="mailto:info@justai-atlas.online?subject=ATLAS%20ULTIMATE%20Enterprise">Contact sales</a>
    </div>
  </div>
  <div class="notice">Payments purchase access to read-only market intelligence. They do not enable trade execution or guarantee market outcomes.</div>
</section>
<style>@media(max-width:1180px){{.plans-grid{{grid-template-columns:repeat(2,minmax(0,1fr))!important}}}}@media(max-width:700px){{.plans-grid{{grid-template-columns:1fr!important}}}}</style>
'''
    scripts = (
        '<script src="/ui/preferences.js"></script>'
        '<script src="/ui/agent-panel.js"></script>'
        '<script src="/ui/demo-panel.js"></script>'
    )
    html = DASHBOARD_HTML.replace('href="/subscribe"', 'href="#plans"')
    html = html.replace("</main>", plans + "</main>")
    return html.replace("</body>", scripts + "</body>")


@router.get(CANONICAL_ATLAS_PATH, response_class=HTMLResponse, tags=["dashboard"], include_in_schema=False)
def atlas_ultimate_view() -> HTMLResponse:
    return HTMLResponse(_atlas_ultimate_html())


@router.get("/dashboard", include_in_schema=False)
def legacy_dashboard_redirect() -> RedirectResponse:
    return RedirectResponse(url=CANONICAL_ATLAS_PATH, status_code=308)


router.include_router(api_router)
router.include_router(agent_panel_router)
router.include_router(demo_panel_router)

__all__ = ["router", "mt5_state", "CANONICAL_ATLAS_PATH"]

# Compatibility API for the read-only analysis demo. No orders or ledger writes.
ATLAS_DEMO_SYMBOLS = ["XAUUSD", "GAS", "XAGUSD", "EURUSD", "XRPUSDT", "SOLUSDT"]


@router.get("/dashboard/mt5-state")
def mt5_state():
    """Expose MT5 dashboard telemetry through a hard read-only boundary."""
    from app.dashboard import api as dashboard_api

    state = dashboard_api.atlas_dashboard_state()
    state["mode"] = "READ_ONLY"
    state["execution"] = "disabled"
    services = dict(state.get("services") or {{}})
    services["execution_gate"] = "DISABLED"
    services["subscriber_access"] = "READ_ONLY"
    state["services"] = services
    return state


def _demo_regime_from_technical(technical):
    from app.intelligence.regime.engine import MarketRegimeEngine, MarketState

    direction = {{"bullish": 0.8, "bearish": -0.8}}
    price = float(technical.get("price") or 0)
    atr = float((technical.get("indicators") or {{}}).get("atr_14") or 0)
    state = MarketState(
        trend_score=direction.get(str(technical.get("trend", "")).lower(), 0.0),
        momentum_score=direction.get(str(technical.get("momentum", "")).lower(), 0.0),
        volatility_score=min(1.0, max(0.0, atr / price * 10)) if price > 0 else 0.0,
        volume_score={{"high": 0.8, "normal": 0.0, "low": -0.5}}.get(
            str(technical.get("volume_state", "")).lower(), 0.0),
        event_risk_score=0.0,
        risk_sentiment_score=0.0,
    )
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
    return {{
        "symbol": symbol, "interval": interval,
        "status": candidate["status"],
        "technical": technical, "structure": structure,
        "regime": _demo_regime_from_technical(technical),
        "signal": signal, "trade_candidate": candidate,
        "execution": "disabled",
        "data_source": "Public market provider; commodity prices may be futures proxies.",
    }}


def atlas_demo_state(interval="15m", account_balance=10000.0):
    import math

    if interval not in {{"5m", "15m", "30m", "1h"}}:
        raise ValueError("Unsupported demo interval")
    if not math.isfinite(account_balance) or account_balance <= 0:
        raise ValueError("Account balance must be positive and finite")
    results = []
    for symbol in ATLAS_DEMO_SYMBOLS:
        try:
            results.append(_analyze_demo_symbol(symbol, interval, account_balance))
        except Exception:
            results.append({{"symbol": symbol, "interval": interval,
                            "status": "ERROR", "error": "Market analysis unavailable"}})
    errors = sum(item["status"] == "ERROR" for item in results)
    return {{
        "status": "DEMO_READY" if errors < len(results) else "DEMO_UNAVAILABLE",
        "execution": "disabled",
        "results": results,
        "summary": {{
            "analyzed": len(results),
            "no_trades": sum(item["status"] == "NO_TRADE" for item in results),
            "errors": errors,
        }},
        "disclaimer": "Read-only analysis, not executed demo trades or verified performance.",
    }}
