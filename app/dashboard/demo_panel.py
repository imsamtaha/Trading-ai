"""Read-only paper-session progress, distinct from broker account telemetry."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.paper_trading.mt5_ledger import MT5PaperLedger, PaperLedgerError
from app.paper_trading.readiness import evaluate_demo_readiness

router = APIRouter()


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
        summary = ledger.summary()
        readiness = evaluate_demo_readiness(ledger.closed_trades())
        return {
            "session": session,
            "summary": summary,
            "readiness": readiness,
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
.demo-session{margin:0 0 18px;border-color:#ff7a1a55;position:relative;overflow:hidden}
.demo-session:before{content:"";position:absolute;width:320px;height:320px;right:-170px;top:-190px;border-radius:50%;background:radial-gradient(circle,#ff7a1a24,transparent 68%);pointer-events:none}
.demo-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;position:relative;z-index:1}
.demo-title{font-size:22px;font-weight:950;margin-top:4px}.demo-status{display:inline-flex;align-items:center;gap:7px;border:1px solid #465469;border-radius:999px;padding:8px 11px;font-size:11px;font-weight:900;letter-spacing:.04em;background:#0a1018cc}.demo-dot{width:8px;height:8px;border-radius:50%;background:var(--yellow);box-shadow:0 0 12px currentColor}.demo-status.online{color:var(--green);border-color:#39d98a55}.demo-status.online .demo-dot{background:var(--green)}.demo-status.stale{color:var(--yellow)}.demo-status.offline{color:var(--red);border-color:#ff617455}.demo-status.offline .demo-dot{background:var(--red)}
.demo-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-top:15px;position:relative;z-index:1}.demo-metric{border:1px solid var(--line);border-radius:14px;padding:12px;background:#080d14aa}.demo-value{font-size:19px;font-weight:950;margin-top:6px}.demo-meta{display:grid;grid-template-columns:1.2fr .8fr;gap:10px;margin-top:10px}.demo-events{margin:8px 0 0;padding-left:18px;color:var(--muted)}.demo-events li{margin:5px 0}.demo-gate{border-left:3px solid var(--orange);padding:11px 13px;background:#ff7a1a0b;border-radius:10px;line-height:1.5}.demo-foot{margin-top:10px;font-size:11px;color:var(--muted)}
@media(max-width:1000px){.demo-metrics{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.demo-metrics{grid-template-columns:1fr 1fr}.demo-meta{grid-template-columns:1fr}}
`;
document.head.append(style);

const panel=document.createElement('section');
panel.className='card demo-session';
panel.id='demo-session';
panel.innerHTML=`
<div class="demo-head">
  <div><div class="label">FORWARD DEMO VALIDATION</div><div class="demo-title">ATLAS Demo Trading</div><div class="mini">MT5 market quotes · local paper ledger · subscriber execution isolated</div></div>
  <div class="demo-status" id="demoStatus"><span class="demo-dot"></span><span id="demoStatusText">CONNECTING</span></div>
</div>
<div class="demo-metrics">
  <div class="demo-metric"><div class="label">Open Paper Trades</div><div class="demo-value" id="demoOpen">—</div></div>
  <div class="demo-metric"><div class="label">Closed Trades</div><div class="demo-value" id="demoClosed">—</div></div>
  <div class="demo-metric"><div class="label">Review Target</div><div class="demo-value" id="demoTarget">—</div></div>
  <div class="demo-metric"><div class="label">Profit Factor</div><div class="demo-value" id="demoPF">—</div></div>
  <div class="demo-metric"><div class="label">Expectancy</div><div class="demo-value" id="demoExpectancy">—</div></div>
  <div class="demo-metric"><div class="label">Drawdown / Risk</div><div class="demo-value" id="demoDD">—</div></div>
</div>
<div class="demo-meta">
  <div><div class="label">Latest Demo Events</div><ul class="demo-events" id="demoEvents"><li>Loading session activity…</li></ul></div>
  <div><div class="label">Live Readiness Gate</div><div class="demo-gate" id="demoReadiness">Evaluating demo evidence…</div><div class="demo-foot" id="demoUpdated">Last update: —</div></div>
</div>`;

const hero=root.querySelector('.hero');
if(hero&&hero.parentNode===root)hero.insertAdjacentElement('afterend',panel);else root.prepend(panel);

const byId=id=>document.getElementById(id);
const fmt=v=>v==null||Number.isNaN(Number(v))?'—':Number(v).toFixed(2);
function setStatus(value){
  const box=byId('demoStatus'),text=byId('demoStatusText');
  const status=String(value||'UNKNOWN').toUpperCase();
  text.textContent=status;
  box.className='demo-status '+((status==='RUNNING'||status==='ONLINE'||status==='ACTIVE')?'online':status==='STALE'?'stale':status==='NOT_STARTED'?'stale':'offline');
  const heroStatus=document.getElementById('status');
  if(heroStatus&&(status==='RUNNING'||status==='ACTIVE'))heroStatus.textContent='DEMO ACTIVE';
}
async function refreshDemo(){
  try{
    const response=await fetch('/dashboard/demo-status',{cache:'no-store'});
    if(!response.ok)throw Error('Demo status unavailable');
    const data=await response.json(),r=data.readiness||{},s=data.summary||{},session=data.session||{};
    setStatus(session.status);
    byId('demoOpen').textContent=s.open_positions??0;
    byId('demoClosed').textContent=s.closed_trades??0;
    byId('demoTarget').textContent=r.required_closed_trades??'—';
    byId('demoPF').textContent=fmt(r.profit_factor);
    byId('demoExpectancy').textContent=fmt(r.expectancy);
    byId('demoDD').textContent=fmt(r.max_drawdown_percent_of_total_risk)+'%';
    const list=byId('demoEvents');list.replaceChildren();
    const events=(session.events||[]).slice(-6).reverse();
    if(!events.length){const li=document.createElement('li');li.textContent='No demo event recorded in the latest cycle.';list.append(li)}
    for(const e of events){const li=document.createElement('li');li.textContent=(e.symbol||'Market')+': '+(e.status||'UPDATE')+(e.reason?' — '+e.reason:'');list.append(li)}
    byId('demoReadiness').textContent='Review gate: '+(r.decision||'UNKNOWN')+' · Automatic live activation: OFF. Demo evidence must pass the documented risk gate before any separate live-execution review.';
    byId('demoUpdated').textContent='Last update: '+(session.updated_at||'not started')+' · Mode: '+(data.mode||'PAPER_DEMO');
  }catch(error){
    setStatus('OFFLINE');
    byId('demoReadiness').textContent='Demo telemetry is unavailable. Readiness is unknown and live activation remains disabled.';
    byId('demoEvents').innerHTML='<li>Could not load the local demo ledger.</li>';
  }
}
refreshDemo();setInterval(refreshDemo,30000);
})();
"""
