from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS — Trading Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#06080d;--card:#0d131d;--line:#253247;--text:#f2f5f9;--muted:#8e9bad;--orange:#ff8a24;--green:#39d98a;--red:#ff6174;--yellow:#f6c85f}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#172336 0,#06080d 42%);color:var(--text);font:14px Inter,system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.brand{display:flex;gap:12px;align-items:center}.logo{width:46px;height:46px;border:1px solid var(--orange);border-radius:15px;display:grid;place-items:center;font-weight:900;color:var(--orange)}.title{font-size:23px;font-weight:900;letter-spacing:.05em}.sub,.mini{font-size:11px;color:var(--muted)}.actions{display:flex;gap:8px;align-items:center}.btn{color:#090b0f;background:var(--orange);text-decoration:none;padding:10px 13px;border-radius:11px;font-weight:900}.badge{border:1px solid var(--line);padding:9px 11px;border-radius:999px;font-weight:800}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(6,1fr)}.split{grid-template-columns:1.65fr 1fr}.market-grid{grid-template-columns:1.25fr 1fr}.card{background:linear-gradient(180deg,#111824,#0b111a);border:1px solid var(--line);border-radius:17px;padding:16px;box-shadow:0 16px 45px #0006}.label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.11em}.big{font-size:24px;font-weight:900;margin-top:6px}.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.orange{color:var(--orange)}.row{display:grid;grid-template-columns:1.2fr .8fr .7fr .7fr .65fr;gap:8px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}.pos{display:grid;grid-template-columns:1fr .65fr .75fr .7fr;gap:8px;padding:9px 0;border-bottom:1px solid var(--line)}.market{display:grid;grid-template-columns:1.2fr .9fr .75fr .7fr;gap:8px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}.news{padding:11px 0;border-bottom:1px solid var(--line)}.news a{color:var(--text);text-decoration:none;font-weight:750}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px}.empty{color:var(--muted);padding:12px 0}.notice{border-left:3px solid var(--orange);padding:10px 12px;background:#ff8a240b;border-radius:8px;color:#bdc7d3;margin-top:12px}.section-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:4px}@media(max-width:1100px){.stats{grid-template-columns:repeat(3,1fr)}.split,.market-grid{grid-template-columns:1fr}}@media(max-width:720px){main{padding:12px}.stats{grid-template-columns:1fr 1fr}.top{align-items:flex-start;flex-direction:column}.row,.pos,.market{grid-template-columns:1fr 1fr}}
</style></head><body><main>
<div class="top"><div class="brand"><div class="logo">A</div><div><div class="title">ATLAS THE ULTIMATE</div><div class="sub">MT5 cockpit · Wall Street board · risk-first intelligence</div></div></div><div class="actions"><a class="btn" href="/subscribe">Plans</a><div class="badge" id="status">CONNECTING</div></div></div>
<div class="grid stats"><div class="card"><div class="label">Account Type</div><div class="big" id="accountType">—</div></div><div class="card"><div class="label">Equity</div><div class="big" id="equity">—</div></div><div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div><div class="card"><div class="label">Floating P/L</div><div class="big" id="floating">—</div></div><div class="card"><div class="label">Open Positions</div><div class="big" id="openPositions">—</div></div><div class="card"><div class="label">Execution Gate</div><div class="big yellow" id="execution">—</div></div></div>
<div class="grid split" style="margin-top:12px"><section class="card"><div class="label">ATLAS Opportunity Matrix</div><div id="signals"></div></section><section class="card"><div class="label">Verified MT5 Account</div><div id="account"></div><div class="label" style="margin-top:18px">Open Positions</div><div id="positions"></div></section></div>
<div class="grid market-grid" style="margin-top:12px"><section class="card"><div class="section-head"><div class="label">Wall Street Board</div><span class="tag" id="marketStatus">LOADING</span></div><div class="mini" id="marketMeta">Provider data</div><div id="markets"></div></section><section class="card"><div class="section-head"><div class="label">Financial News</div><span class="mini" id="newsMeta"></span></div><div id="news"></div></section></div>
<div class="notice" id="disclaimer">Read-only telemetry. Trading involves risk.</div></main>
<script>
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const money=(value,currency='')=>value===null||value===undefined?'PRIVATE':Number(value).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+(currency?' '+currency:'');
const tone=value=>Number(value)>=0?'green':'red';
const stamp=value=>value?new Date(value).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'—';

function renderMarkets(financial){
  const state=financial||{};
  $('marketStatus').textContent=state.status||'UNAVAILABLE';
  $('marketStatus').className='tag '+((state.status==='LIVE')?'green':(state.status==='NOT_CONFIGURED'?'yellow':'red'));
  $('marketMeta').textContent=(state.data_label||'Provider data')+' · refreshed '+stamp(state.generated_at)+(state.cached?' · cached':'');
  const items=state.markets||[];
  $('markets').innerHTML=items.map(item=>'<div class="market"><div><b>'+esc(item.label)+'</b><div class="mini">'+esc(item.symbol)+' · '+esc(item.group)+'</div></div><div><b>'+esc(item.last)+'</b><div class="mini">last</div></div><div class="'+tone(item.change)+'"><b>'+Number(item.change||0).toFixed(2)+'</b><div class="mini">change</div></div><div class="'+tone(item.change_percent)+'"><b>'+Number(item.change_percent||0).toFixed(2)+'%</b><div class="mini">session</div></div></div>').join('')||'<div class="empty">'+esc(state.message||'Market board unavailable.')+'</div>';
  const news=state.news||[];
  $('newsMeta').textContent=state.source?esc(state.source):'';
  $('news').innerHTML=news.map(item=>'<article class="news"><a href="'+esc(item.url)+'" target="_blank" rel="noopener noreferrer">'+esc(item.headline)+'</a><div class="mini">'+esc(item.source)+' · '+stamp(item.published_at)+'</div></article>').join('')||'<div class="empty">'+esc(state.message||'Financial news unavailable.')+'</div>';
}

async function refresh(){
  try{
    const response=await fetch('/dashboard/atlas',{cache:'no-store'});
    if(!response.ok)throw Error('HTTP '+response.status);
    const data=await response.json(), account=data.account||{};
    $('status').textContent=data.verified_live_account?'VERIFIED LIVE':'ONLINE';
    $('accountType').textContent=account.account_type||'—';
    $('accountType').className='big '+(account.account_type==='REAL'?'green':'yellow');
    $('equity').textContent=money(account.equity,account.currency);
    $('balance').textContent=money(account.balance,account.currency);
    $('floating').textContent=money(data.floating_position_pnl,account.currency);
    $('floating').className='big '+tone(data.floating_position_pnl);
    $('openPositions').textContent=data.open_positions??0;
    $('execution').textContent=(data.services||{}).execution_gate||'DISABLED';
    $('account').innerHTML='<div class="pos"><span>'+esc(account.label)+'</span><b>'+esc(account.login)+'</b><span>'+esc(account.server)+'</span><b>1:'+esc(account.leverage||'—')+'</b></div>';
    $('signals').innerHTML=(data.symbols||[]).map(item=>'<div class="row"><div><b>'+esc(item.canonical_symbol||item.symbol)+'</b><div class="mini">'+esc(item.asset_class)+' · '+esc(item.symbol)+'</div></div><div><span class="tag">'+esc(item.decision.bias)+'</span><div class="mini">'+esc(item.decision.decision)+'</div></div><div><b>'+Number(item.decision.score||0).toFixed(1)+'</b><div class="mini">score</div></div><div><b>'+Number(item.quality.execution_confidence||0).toFixed(1)+'%</b><div class="mini">confidence</div></div><div><b>'+Number(item.opportunity_score||0).toFixed(0)+'</b><div class="mini">opportunity</div></div></div>').join('')||'<div class="empty">No MT5 markets available.</div>';
    $('positions').innerHTML=(data.positions||[]).map(position=>'<div class="pos"><div><b>'+esc(position.symbol)+'</b><div class="mini">'+esc(position.direction)+'</div></div><div>'+esc(position.volume)+'</div><div>'+esc(position.price_open)+'</div><div class="'+tone(position.profit)+'"><b>'+Number(position.profit||0).toFixed(2)+'</b></div></div>').join('')||'<div class="empty">No open positions.</div>';
    $('disclaimer').textContent=data.disclaimer;
    renderMarkets(data.financial_market);
  }catch(error){
    $('status').textContent='OFFLINE';
    $('marketStatus').textContent='OFFLINE';
  }
}
refresh();setInterval(refresh,5000);
</script></body></html>'''
