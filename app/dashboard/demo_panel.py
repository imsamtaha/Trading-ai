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
        session = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "NOT_STARTED"}
        if not isinstance(session, dict):
            raise ValueError("Invalid session status")
        if session.get("updated_at"):
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(session["updated_at"])).total_seconds()
            if age > max(90, 3 * int(session.get("cycle_seconds", 30))):
                session["status"] = "STALE"
        ledger = MT5PaperLedger()
        return {"session": session, "summary": ledger.summary(),
                "readiness": evaluate_demo_readiness(ledger.closed_trades()),
                "mode": "PAPER_DEMO", "automatic_live_activation": False,
                "description": "Local simulated trades using MT5 quotes. No broker orders."}
    except (ValueError, OSError, TypeError, PaperLedgerError):
        raise HTTPException(503, "Demo status unavailable; do not infer readiness.")


@router.get("/ui/demo-panel.js", include_in_schema=False)
def script():
    return Response(SCRIPT, media_type="application/javascript")


SCRIPT = r"""
(()=>{
const root=document.querySelector('main');if(!root)return;
const panel=document.createElement('section');panel.className='card';panel.id='demo-session';
panel.innerHTML='<h2>ATLAS Demo Session</h2><p>Local paper ledger · MT5 quotes · No broker orders</p><p id="demo-progress">Loading session status...</p><ul id="demo-events"></ul><p id="demo-readiness"></p>';
root.prepend(panel);
async function refresh(){try{
const response=await fetch('/dashboard/demo-status',{cache:'no-store'});if(!response.ok)throw Error();
const data=await response.json(),r=data.readiness,s=data.summary;
document.getElementById('demo-progress').textContent=data.session.status+' | Open paper trades: '+s.open_positions+' | Closed: '+s.closed_trades+' / '+r.required_closed_trades+' | Updated: '+(data.session.updated_at||'not started');
const list=document.getElementById('demo-events');list.replaceChildren();
for(const e of data.session.events||[]){const li=document.createElement('li');li.textContent=e.symbol+': '+e.status+' — '+(e.reason||'');list.append(li)}
document.getElementById('demo-readiness').textContent='Review gate: '+r.decision+' | Profit factor: '+r.profit_factor+' | Expectancy: '+r.expectancy+' | Drawdown / total risk: '+r.max_drawdown_percent_of_total_risk+'%. Live activation remains disabled. Paper results are not broker fills.';
}catch{document.getElementById('demo-progress').textContent='Demo status unavailable';document.getElementById('demo-events').replaceChildren();document.getElementById('demo-readiness').textContent='Readiness unknown. Live activation remains disabled.'}}
refresh();setInterval(refresh,30000);
})();
"""
