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
    return '<span class="btn ghost" aria-disabled="true" title="Stripe checkout becomes available after account verification">Stripe activation pending</span>'


def _atlas_ultimate_html() -> str:
    watch_stripe = _stripe_button("watch")
    signals_stripe = _stripe_button("reader")
    pro_stripe = _stripe_button("pro")
    plans = f'''
<section id="plans" class="card atlas-plans" style="margin-top:18px">
  <div class="label">ATLAS ULTIMATE ACCESS</div>
  <h2 style="font-size:clamp(28px,4vw,48px);margin:8px 0 6px">Choose your intelligence level.</h2>
  <p class="mini" style="max-width:820px;font-size:13px;line-height:1.6">Three paid intelligence levels. No free demo and no free trial. Market information is decision-support; broker execution remains under the trader's control.</p>
  <div class="plans-grid">
    <div class="card plan-card">
      <div class="label">Market Watch</div><div class="big">$29<span class="mini"> / month</span></div>
      <p class="mini">Live financial news board · Market direction and bias · Market structure · Key levels · Strategy and setup context.</p>
      {watch_stripe}
      <a class="btn ghost" href="/billing/whish/watch">Whish Money</a>
    </div>
    <div class="card plan-card" style="border-color:#ff7a1a66">
      <div class="label">ATLAS Signals</div><div class="big">$49<span class="mini"> / month</span></div>
      <p class="mini">Everything in Market Watch · Manual-execution signals · Entry/reference zones · Targets · Stop/invalidation levels · Risk and confidence context.</p>
      {signals_stripe}
      <a class="btn ghost" href="/billing/whish/reader">Whish Money</a>
    </div>
    <div class="card plan-card">
      <div class="label">ATLAS Pro</div><div class="big">$99<span class="mini"> / month</span></div>
      <p class="mini">Everything in Signals · Continuous multi-asset analysis · Opportunity matrix · Risk/position monitoring · Exit and stop alerts · Priority intelligence briefings.</p>
      {pro_stripe}
      <a class="btn ghost" href="/billing/whish/pro">Whish Money</a>
    </div>
    <div class="card plan-card">
      <div class="label">Enterprise</div><div class="big">Custom</div>
      <p class="mini">Manual application and review · Team access · Custom integrations and deployment planning · Commercial quote based on required services.</p>
      <a class="btn ghost" href="mailto:info@justai-atlas.online?subject=ATLAS%20ULTIMATE%20Enterprise%20Application">Apply / Contact CEO</a>
    </div>
  </div>
  <div class="notice">Subscriptions provide market intelligence and monitoring. They do not guarantee outcomes or authorize public subscriber broker execution.</div>
</section>
<style>
.plans-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}}.plan-card{{box-shadow:none;display:flex;flex-direction:column;gap:12px;position:relative;overflow:hidden}}.plan-card:before{{content:"";position:absolute;inset:-80% 45% auto -30%;height:220px;background:radial-gradient(circle,#ff7a1a1f,transparent 68%);pointer-events:none}}.atlas-tech-bg{{position:fixed;inset:0;z-index:-1;pointer-events:none;perspective:900px;overflow:hidden}}.atlas-tech-bg:before{{content:"";position:absolute;left:-15%;right:-15%;bottom:-36%;height:72%;transform:rotateX(64deg);transform-origin:center top;background-image:linear-gradient(#ff7a1a14 1px,transparent 1px),linear-gradient(90deg,#91a4bd12 1px,transparent 1px);background-size:58px 58px;filter:drop-shadow(0 0 14px #ff7a1a18)}}.atlas-tech-bg:after{{content:"";position:absolute;width:560px;height:560px;right:-180px;top:20%;border:1px solid #ff7a1a20;border-radius:50%;box-shadow:0 0 80px #ff7a1a12,inset 0 0 80px #91a4bd0b}}.refresh-sector{{margin-left:10px;min-height:30px;padding:5px 10px;font-size:11px;cursor:pointer}}.refresh-sector.loading{{opacity:.55;pointer-events:none}}.last-updated{{font-size:10px;color:var(--muted);margin-left:8px}}@media(max-width:1180px){{.plans-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:700px){{.plans-grid{{grid-template-columns:1fr}}}}
</style>
'''
    refresh_script = r'''
<script>
(function(){
  function stamp(btn){var s=btn.parentElement.querySelector('.last-updated');if(s)s.textContent='Updated '+new Date().toLocaleTimeString();}
  function addButton(title,fn){if(!title||title.querySelector('.refresh-sector'))return;var b=document.createElement('button');b.className='btn ghost refresh-sector';b.type='button';b.textContent='↻ Refresh';var s=document.createElement('span');s.className='last-updated';s.textContent='';b.onclick=async function(){b.classList.add('loading');b.textContent='Refreshing…';try{await fn();stamp(b)}finally{b.classList.remove('loading');b.textContent='↻ Refresh'}};title.appendChild(b);title.appendChild(s)}
  var titles=[].slice.call(document.querySelectorAll('.section-title'));
  titles.forEach(function(t){var text=t.textContent.toLowerCase();addButton(t,text.indexOf('wall street')>=0||text.indexOf('news')>=0?function(){return window.refreshBriefing?window.refreshBriefing():Promise.resolve()}:function(){return window.refresh?window.refresh():Promise.resolve()})});
  var actions=document.querySelector('.actions');if(actions){var all=document.createElement('button');all.className='btn ghost';all.type='button';all.textContent='↻ Refresh All';all.onclick=async function(){all.textContent='Refreshing…';try{if(window.refresh)await window.refresh();if(window.refreshBriefing)await window.refreshBriefing();all.textContent='✓ Updated';setTimeout(function(){all.textContent='↻ Refresh All'},1200)}catch(e){all.textContent='Retry Refresh'}};actions.prepend(all)}
})();
</script>
'''
    scripts = '<script src="/ui/preferences.js"></script><script src="/ui/agent-panel.js"></script><script src="/ui/demo-panel.js"></script>'
    html = DASHBOARD_HTML.replace('href="/subscribe"', 'href="#plans"')
    html = html.replace('<body>', '<body><div class="atlas-tech-bg" aria-hidden="true"></div>')
    html = html.replace('</main>', plans + '</main>') if '</main>' in html else html.replace('<div class="notice" id="disclaimer">', plans + '<div class="notice" id="disclaimer">')
    return html.replace('</body>', refresh_script + scripts + '</body>')


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

ATLAS_DEMO_SYMBOLS = ["XAUUSD", "GAS", "XAGUSD", "EURUSD", "XRPUSDT", "SOLUSDT"]


@router.get("/dashboard/mt5-state")
def mt5_state():
    """Expose MT5 dashboard telemetry through a hard read-only boundary."""
    from app.dashboard import api as dashboard_api
    state = dashboard_api.atlas_dashboard_state()
    state["mode"] = "READ_ONLY"
    state["execution"] = "disabled"
    services = dict(state.get("services") or {})
    services["execution_gate"] = "DISABLED"
    services["subscriber_access"] = "READ_ONLY"
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
