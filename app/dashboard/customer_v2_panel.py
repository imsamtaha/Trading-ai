from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

COUNCIL_PANEL = r'''
<section id="atlas-council-panel" class="card" style="margin-top:18px">
  <div class="label">ATLAS REALTIME AGENT COUNCIL</div>
  <h2 style="margin:8px 0">ATLAS Intelligence Council</h2>
  <p class="mini">Realtime decision, confidence, agent health, rescue state and customer positions.</p>
  <div class="grid" style="margin-top:14px">
    <div class="card"><div class="label">Decision</div><div class="big" id="council-decision">?</div><div class="mini" id="council-confidence">Confidence ?</div></div>
    <div class="card"><div class="label">Agents</div><div class="big" id="council-agents">?</div><div class="mini" id="council-agent-status">Waiting for account</div></div>
    <div class="card"><div class="label">Rescue</div><div class="big" id="council-rescue">?</div><div class="mini">Independent position monitor</div></div>
    <div class="card"><div class="label">Positions</div><div class="big" id="council-positions">0</div><div class="mini" id="council-account">Sign in to load your account</div></div>
  </div>
  <div class="notice" id="council-message" style="margin-top:12px">Waiting for authenticated customer session.</div>
</section>
'''

SCRIPT = r'''
(()=>{
const byId=id=>document.getElementById(id);
async function authState(){const api=window.atlasAuth;if(!api||!api.getSession)return null;const session=await api.getSession();return session&&session.access_token&&session.user?session:null;}
async function load(){
  const msg=byId('council-message'); if(!msg)return; const session=await authState();
  if(!session){msg.textContent='Sign in to load ATLAS Intelligence Council.';return;}
  const auth={Authorization:'Bearer '+session.access_token};
  const accountRes=await fetch('/api/v2/customer/accounts',{headers:auth,cache:'no-store'});
  if(!accountRes.ok){msg.textContent='Customer account mapping is unavailable.';return;}
  const accounts=(await accountRes.json()).accounts||[]; if(!accounts.length){msg.textContent='No linked LIVE_DEMO account was found for this user.';return;}
  const a=accounts[0], headers={...auth,'X-Customer-ID':a.customer_id,'X-Account-ID':a.account_id};
  const [d,s,r,p]=await Promise.all([fetch('/api/v2/customer/decisions/latest',{headers,cache:'no-store'}),fetch('/api/v2/customer/agents/status',{headers,cache:'no-store'}),fetch('/api/v2/customer/rescue/status',{headers,cache:'no-store'}),fetch('/api/v2/customer/positions',{headers,cache:'no-store'})]);
  if(![d,s,r,p].every(x=>x.ok)){msg.textContent='Realtime council state is temporarily unavailable.';return;}
  const decision=await d.json(), agents=await s.json(), rescue=await r.json(), positions=await p.json();
  byId('council-decision').textContent=decision.decision||'WAIT'; byId('council-confidence').textContent='Confidence '+Math.round(Number(decision.confidence||0)*100)+'%';
  byId('council-agents').textContent=(agents.agents||[]).length; byId('council-agent-status').textContent=agents.status||'READY'; byId('council-rescue').textContent=rescue.action||'HOLD';
  byId('council-positions').textContent=(positions.positions||[]).length; byId('council-account').textContent=a.account_id+' ? '+a.mode; msg.textContent='Realtime customer intelligence is connected.';
}
window.addEventListener('atlas-auth-change',load); document.addEventListener('DOMContentLoaded',load); load();
})();
'''

@router.get('/ui/customer-v2-panel.js', include_in_schema=False)
def customer_v2_panel_js():
    return Response(SCRIPT, media_type='application/javascript')
