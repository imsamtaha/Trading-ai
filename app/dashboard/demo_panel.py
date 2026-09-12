"""Read-only paper-session progress, distinct from broker account telemetry."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError
from app.paper_trading.readiness import evaluate_demo_readiness

router = APIRouter()


def _performance_metrics(closed_trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Build risk-normalized demo performance metrics without broker P&L claims."""
    trades = sorted(
        (dict(t) for t in closed_trades),
        key=lambda trade: str(trade.get("closed_at") or ""),
    )
    cumulative = 0.0
    equity_curve: list[float] = []
    asset_pnl: dict[str, float] = {}
    wins = 0

    for trade in trades:
        pnl = float(trade.get("risk_normalized_pnl", 0.0) or 0.0)
        cumulative += pnl
        equity_curve.append(round(cumulative, 2))
        symbol = str(trade.get("symbol") or "UNKNOWN")
        asset_pnl[symbol] = asset_pnl.get(symbol, 0.0) + pnl
        if pnl > 0:
            wins += 1

    ranked = sorted(asset_pnl.items(), key=lambda item: item[1])
    best = ranked[-1] if ranked else None
    worst = ranked[0] if ranked else None
    count = len(trades)

    return {
        "total_pnl": round(cumulative, 2),
        "win_rate": round((wins / count * 100.0) if count else 0.0, 2),
        "average_pnl": round((cumulative / count) if count else 0.0, 2),
        "equity_curve": equity_curve,
        "best_asset": {"symbol": best[0], "pnl": round(best[1], 2)} if best else None,
        "worst_asset": {"symbol": worst[0], "pnl": round(worst[1], 2)} if worst else None,
        "recent_closed_trades": list(reversed(trades[-10:])),
        "metric_basis": "risk_normalized_pnl",
    }


@router.get("/dashboard/demo-status")
def demo_status():
    try:
        path = Path(os.getenv("ATLAS_DEMO_STATUS", "data/atlas_demo_status.json"))
        session = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else {"status": "NOT_STARTED"}
        )
        if not isinstance(session, dict):
            raise ValueError("Invalid session status")
        if session.get("updated_at"):
            age = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(session["updated_at"])
            ).total_seconds()
            if age > max(90, 3 * int(session.get("cycle_seconds", 30))):
                session["status"] = "STALE"

        ledger = MT5PaperLedger()
        closed_trades = ledger.closed_trades()
        summary = ledger.summary()
        readiness = evaluate_demo_readiness(closed_trades)
        performance = _performance_metrics(closed_trades)
        return {
            "session": session,
            "summary": summary,
            "readiness": readiness,
            "performance": performance,
            "mode": "PAPER_DEMO",
            "automatic_live_activation": False,
            "description": "Local simulated trades using MT5 quotes. No broker orders.",
        }
    except (ValueError, OSError, TypeError, PaperLedgerError):
        raise HTTPException(503, "Demo status unavailable; do not infer readiness.")


@router.get("/ui/demo-panel.js", include_in_schema=False)
def script():
    return Response(SCRIPT, media_type="application/javascript")


SCRIPT = r"""
(()=>{
const root=document.querySelector('.shell')||document.querySelector('main')||document.body;
if(!root||document.getElementById('demo-session'))return;

const style=document.createElement('style');
style.textContent=`
.demo-session{margin:0 0 18px;border-color:#ff7a1a55;position:relative;overflow:hidden}.demo-session:before{content:"";position:absolute;width:320px;height:320px;right:-170px;top:-190px;border-radius:50%;background:radial-gradient(circle,#ff7a1a24,transparent 68%);pointer-events:none}.demo-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;position:relative;z-index:1}.demo-title{font-size:22px;font-weight:950;margin-top:4px}.demo-status{display:inline-flex;align-items:center;gap:7px;border:1px solid #465469;border-radius:999px;padding:8px 11px;font-size:11px;font-weight:900;letter-spacing:.04em;background:#0a1018cc}.demo-dot{width:8px;height:8px;border-radius:50%;background:var(--yellow);box-shadow:0 0 12px currentColor}.demo-status.online{color:var(--green);border-color:#39d98a55}.demo-status.online .demo-dot{background:var(--green)}.demo-status.stale{color:var(--yellow)}.demo-status.offline{color:var(--red);border-color:#ff617455}.demo-status.offline .demo-dot{background:var(--red)}
.demo-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-top:15px;position:relative;z-index:1}.demo-metric{border:1px solid var(--line);border-radius:14px;padding:12px;background:#080d14aa}.demo-value{font-size:19px;font-weight:950;margin-top:6px}.demo-meta{display:grid;grid-template-columns:1.2fr .8fr;gap:10px;margin-top:10px}.demo-events{margin:8px 0 0;padding-left:18px;color:var(--muted)}.demo-events li{margin:5px 0}.demo-gate{border-left:3px solid var(--orange);padding:11px 13px;background:#ff7a1a0b;border-radius:10px;line-height:1.5}.demo-foot{margin-top:10px;font-size:11px;color:var(--muted)}
.performance-center{margin-top:18px;padding-top:16px;border-top:1px solid var(--line)}.performance-head{display:flex;justify-content:space-between;align-items:end;gap:12px}.performance-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.performance-body{display:grid;grid-template-columns:1.1fr .9fr;gap:10px;margin-top:10px}.equity-box,.history-box{border:1px solid var(--line);border-radius:14px;padding:13px;background:#080d14aa}.equity-svg{width:100%;height:150px;display:block;margin-top:8px}.equity-line{fill:none;stroke:var(--orange);stroke-width:3}.equity-zero{stroke:#63708366;stroke-width:1;stroke-dasharray:4 5}.trade-row{display:grid;grid-template-columns:1fr .7fr .7fr .8fr;gap:8px;padding:8px 0;border-bottom:1px solid var(--line);font-size:12px}.trade-row:last-child{border-bottom:0}
@media(max-width:1000px){.demo-metrics{grid-template-columns:repeat(3,1fr)}.performance-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.demo-metrics{grid-template-columns:1fr 1fr}.demo-meta,.performance-body{grid-template-columns:1fr}.performance-grid{grid-template-columns:1fr 1fr}.trade-row{grid-template-columns:1fr 1fr}}
`;
document.head.append(style);

const panel=document.createElement('section');panel.className='card demo-session';panel.id='demo-session';
panel.innerHTML=`
<div class="demo-head"><div><div class="label">FORWARD DEMO VALIDATION</div><div class="demo-title">ATLAS Demo Trading</div><div class="mini">MT5 market quotes · local paper ledger · subscriber execution isolated</div></div><div class="demo-status" id="demoStatus"><span class="demo-dot"></span><span id="demoStatusText">CONNECTING</span></div></div>
<div class="demo-metrics"><div class="demo-metric"><div class="label">Open Paper Trades</div><div class="demo-value" id="demoOpen">—</div></div><div class="demo-metric"><div class="label">Closed Trades</div><div class="demo-value" id="demoClosed">—</div></div><div class="demo-metric"><div class="label">Review Target</div><div class="demo-value" id="demoTarget">—</div></div><div class="demo-metric"><div class="label">Profit Factor</div><div class="demo-value" id="demoPF">—</div></div><div class="demo-metric"><div class="label">Expectancy</div><div class="demo-value" id="demoExpectancy">—</div></div><div class="demo-metric"><div class="label">Drawdown / Risk</div><div class="demo-value" id="demoDD">—</div></div></div>
<div class="demo-meta"><div><div class="label">Latest Demo Events</div><ul class="demo-events" id="demoEvents"><li>Loading session activity…</li></ul></div><div><div class="label">Live Readiness Gate</div><div class="demo-gate" id="demoReadiness">Evaluating demo evidence…</div><div class="demo-foot" id="demoUpdated">Last update: —</div></div></div>
<div class="performance-center"><div class="performance-head"><div><div class="label">DEMO ANALYTICS</div><div class="demo-title">Performance Center</div></div><div class="mini">Risk-normalized paper results · not broker P/L</div></div><div class="performance-grid"><div class="demo-metric"><div class="label">Win Rate</div><div class="demo-value" id="demo-win-rate">—</div></div><div class="demo-metric"><div class="label">Cumulative P/L</div><div class="demo-value" id="demo-total-pnl">—</div></div><div class="demo-metric"><div class="label">Best Asset</div><div class="demo-value" id="demo-best-asset">—</div></div><div class="demo-metric"><div class="label">Worst Asset</div><div class="demo-value" id="demo-worst-asset">—</div></div></div><div class="performance-body"><div class="equity-box"><div class="label">Equity Curve · Risk Normalized</div><svg class="equity-svg" id="demo-equity-chart" viewBox="0 0 600 150" preserveAspectRatio="none"><line class="equity-zero" x1="0" y1="75" x2="600" y2="75"></line><polyline class="equity-line" id="demo-equity-line" points=""></polyline></svg></div><div class="history-box"><div class="label">Recent Closed Trades</div><div id="demo-trade-history"><div class="mini" style="padding:10px 0">No closed trades yet.</div></div></div></div></div>`;

const hero=root.querySelector('.hero');if(hero&&hero.parentNode===root)hero.insertAdjacentElement('afterend',panel);else root.prepend(panel);
const byId=id=>document.getElementById(id);const fmt=v=>v==null||Number.isNaN(Number(v))?'—':Number(v).toFixed(2);const esc=v=>String(v==null?'':v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
function setStatus(value){const box=byId('demoStatus'),text=byId('demoStatusText');const status=String(value||'UNKNOWN').toUpperCase();text.textContent=status;box.className='demo-status '+((status==='RUNNING'||status==='ONLINE'||status==='ACTIVE')?'online':status==='STALE'?'stale':status==='NOT_STARTED'?'stale':'offline');const heroStatus=document.getElementById('status');if(heroStatus&&(status==='RUNNING'||status==='ACTIVE'))heroStatus.textContent='DEMO ACTIVE'}
function drawCurve(values){const line=byId('demo-equity-line');if(!values||!values.length){line.setAttribute('points','');return}const min=Math.min(0,...values),max=Math.max(0,...values),span=(max-min)||1;const points=values.map((v,i)=>{const x=values.length===1?300:i*600/(values.length-1);const y=140-((Number(v)-min)/span)*130;return x.toFixed(1)+','+y.toFixed(1)});line.setAttribute('points',points.join(' '))}
function renderHistory(trades){const box=byId('demo-trade-history');if(!trades||!trades.length){box.innerHTML='<div class="mini" style="padding:10px 0">No closed trades yet.</div>';return}box.innerHTML=trades.map(t=>'<div class="trade-row"><b>'+esc(t.symbol||'—')+'</b><span>'+esc(t.direction||'—')+'</span><span>'+esc(t.exit_reason||'—')+'</span><b class="'+(Number(t.risk_normalized_pnl||0)>=0?'green':'red')+'">'+fmt(t.risk_normalized_pnl)+'</b></div>').join('')}
async function refreshDemo(){try{const response=await fetch('/dashboard/demo-status',{cache:'no-store'});if(!response.ok)throw Error('Demo status unavailable');const data=await response.json(),r=data.readiness||{},s=data.summary||{},session=data.session||{},p=data.performance||{};setStatus(session.status);byId('demoOpen').textContent=s.open_positions??0;byId('demoClosed').textContent=s.closed_trades??0;byId('demoTarget').textContent=r.required_closed_trades??'—';byId('demoPF').textContent=fmt(r.profit_factor);byId('demoExpectancy').textContent=fmt(r.expectancy);byId('demoDD').textContent=fmt(r.max_drawdown_percent_of_total_risk)+'%';const list=byId('demoEvents');list.replaceChildren();const events=(session.events||[]).slice(-6).reverse();if(!events.length){const li=document.createElement('li');li.textContent='No demo event recorded in the latest cycle.';list.append(li)}for(const e of events){const li=document.createElement('li');li.textContent=(e.symbol||'Market')+': '+(e.status||'UPDATE')+(e.reason?' — '+e.reason:'');list.append(li)}byId('demoReadiness').textContent='Review gate: '+(r.decision||'UNKNOWN')+' · Automatic live activation: OFF. Demo evidence must pass the documented risk gate before any separate live-execution review.';byId('demoUpdated').textContent='Last update: '+(session.updated_at||'not started')+' · Mode: '+(data.mode||'PAPER_DEMO');byId('demo-win-rate').textContent=fmt(p.win_rate)+'%';byId('demo-total-pnl').textContent=fmt(p.total_pnl);byId('demo-total-pnl').className='demo-value '+(Number(p.total_pnl||0)>=0?'green':'red');byId('demo-best-asset').textContent=p.best_asset?(p.best_asset.symbol+' · '+fmt(p.best_asset.pnl)):'—';byId('demo-worst-asset').textContent=p.worst_asset?(p.worst_asset.symbol+' · '+fmt(p.worst_asset.pnl)):'—';drawCurve(p.equity_curve||[]);renderHistory(p.recent_closed_trades||[])}catch(error){setStatus('OFFLINE');byId('demoReadiness').textContent='Demo telemetry is unavailable. Readiness is unknown and live activation remains disabled.';byId('demoEvents').innerHTML='<li>Could not load the local demo ledger.</li>';byId('demo-trade-history').innerHTML='<div class="mini">Performance data unavailable.</div>'}}
refreshDemo();setInterval(refreshDemo,30000);
})();
"""
