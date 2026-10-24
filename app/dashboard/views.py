from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
router=APIRouter(tags=["dashboard"])
@router.get("/dashboard",response_class=HTMLResponse)
def dashboard_view()->HTMLResponse:return HTMLResponse(DASHBOARD_HTML.replace("</body>",'<script src="/ui/preferences.js"></script></body>'))
DASHBOARD_HTML=r'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS ULTIMATE — Trading Intelligence</title><style>:root{color-scheme:dark;--bg:#06080d;--line:#2a3545;--text:#f4efe6;--muted:#9ca7b5;--orange:#ff7a1a;--green:#39d98a;--red:#ff6174;--yellow:#f6c85f}*{box-sizing:border-box}body{margin:0;background:#06080d;color:var(--text);font:14px Inter,system-ui,sans-serif}.shell{max-width:1560px;margin:auto;padding:20px}.hero,.card{background:linear-gradient(180deg,#111925,#0a0f17);border:1px solid var(--line);border-radius:19px;padding:18px}.hero{margin-bottom:20px}.top,.section-title,.board-head{display:flex;justify-content:space-between;align-items:center;gap:12px}.title{font-size:28px;font-weight:950}.sub,.mini,.label{color:var(--muted);font-size:11px}.label{text-transform:uppercase;letter-spacing:.12em}.actions{display:flex;gap:8px;flex-wrap:wrap}.btn{border:1px solid #465469;background:#111925;color:var(--text);padding:9px 12px;border-radius:10px;font-weight:800;cursor:pointer}.btn.primary{background:var(--orange);color:#090b0f}.badge,.tag,.freshness{display:inline-block;border:1px solid #435166;border-radius:999px;padding:5px 9px}.freshness{font-size:9px;font-weight:900;letter-spacing:.08em}.freshness.FRESH{color:var(--green);border-color:#39d98a66}.freshness.DELAYED{color:var(--yellow);border-color:#f6c85f66}.freshness.STALE,.freshness.UNAVAILABLE,.freshness.UNKNOWN{color:var(--red);border-color:#ff617466}.section-title{margin:25px 2px 10px}.section-title h2{margin:3px 0}.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(6,1fr)}.split{grid-template-columns:1.5fr 1fr}.big{font-size:24px;font-weight:900;margin-top:7px}.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.row{display:grid;grid-template-columns:1.2fr .8fr .7fr .7fr .65fr;gap:8px;padding:11px 0;border-bottom:1px solid var(--line)}.market{display:grid;grid-template-columns:1.25fr .65fr .55fr .9fr;gap:8px;padding:11px 0;border-bottom:1px solid var(--line);align-items:center}.pos{display:grid;grid-template-columns:1fr .65fr .75fr .7fr;gap:8px;padding:10px 0;border-bottom:1px solid var(--line)}.story{display:block;padding:11px 0;border-bottom:1px solid var(--line);color:var(--text);text-decoration:none;line-height:1.5}.empty{color:var(--muted);padding:14px 0}.notice{border-left:3px solid var(--orange);padding:12px;margin-top:14px}.board-summary{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:12px 0}.summary-chip{border:1px solid var(--line);border-radius:12px;padding:10px;background:#ffffff04}.summary-chip b{display:block;font-size:17px;margin-top:4px}.updated{font-size:10px;color:var(--muted)}.atlas-symbol{direction:ltr;unicode-bidi:isolate;display:inline-block}.quote-time{margin-top:5px;font-size:9px;color:var(--muted)}.analysis-row{display:grid;grid-template-columns:1.1fr 1fr .8fr;gap:8px;padding:12px 0;border-bottom:1px solid var(--line);align-items:start}.analysis-timeframes{grid-column:1/-1;line-height:1.6;overflow-wrap:anywhere}.analysis-value{overflow-wrap:anywhere}@media(max-width:650px){.analysis-row{grid-template-columns:1fr 1fr}.analysis-timeframes{grid-column:1/-1}}@media(max-width:1000px){.stats{grid-template-columns:repeat(3,1fr)}.split{grid-template-columns:1fr}.board-summary{grid-template-columns:repeat(3,1fr)}}@media(max-width:650px){.stats,.board-summary{grid-template-columns:1fr 1fr}.row,.market,.pos{grid-template-columns:1fr 1fr}.top{align-items:flex-start;flex-direction:column}}</style></head><body><div class="shell"><section class="hero"><div class="top"><div><div class="title">ATLAS ULTIMATE</div><div class="sub">JUST AI · Unified Trading Intelligence</div></div><div class="actions"><button class="btn primary" id="refreshAll">Refresh All</button><span class="badge" id="status">CONNECTING</span></div></div></section><div id="hub-account" class="section-title"><div><div class="label">LIVE ACCOUNT TELEMETRY</div><h2>Trading cockpit</h2></div><button class="btn" id="refreshAtlas">Refresh</button></div><div class="grid stats"><div class="card"><div class="label">Account Type</div><div class="big" id="accountType">—</div></div><div class="card"><div class="label">Equity</div><div class="big" id="equity">—</div></div><div class="card"><div class="label">Balance</div><div class="big" id="balance">—</div></div><div class="card"><div class="label">Floating P/L</div><div class="big" id="floating">—</div></div><div class="card"><div class="label">Open Positions</div><div class="big" id="openPositions">—</div></div><div class="card"><div class="label">Execution Gate</div><div class="big yellow" id="execution">—</div></div></div><div class="section-title"><div><div class="label">ATLAS ANALYTICS</div><h2>Opportunity matrix & account state</h2></div></div><div class="grid split"><section class="card"><div class="label">ATLAS Opportunity Matrix</div><div id="signals"></div></section><section class="card"><div class="label">Verified Account</div><div id="brokerAccount"></div><div class="label" style="margin-top:18px">Open Positions</div><div id="positions"></div></section></div><div id="hub-analysis" class="section-title"><div><div class="label">ATLAS INTELLIGENCE · READ ONLY</div><h2 id="analysisHeading">Market Analysis</h2></div><button class="btn" id="refreshAnalysis">Refresh Analysis</button></div><div class="grid split"><section class="card"><div class="board-head"><b id="analysisSignalsHeading">Multi-Timeframe Signals</b><span class="freshness UNKNOWN" id="analysisStatus">WAITING</span></div><div class="mini" id="analysisTime">Source: ATLAS /dashboard/atlas</div><div id="analysisSignals" aria-live="polite"><div class="empty">Loading analysis…</div></div></section><section class="card"><div class="label" id="analysisContextHeading">Market Breadth & Risk Context</div><div class="board-summary"><div class="summary-chip"><span class="mini" id="analysisBreadthLabel">Breadth</span><b id="analysisBreadth">—</b></div><div class="summary-chip"><span class="mini" id="analysisUsableLabel">Usable</span><b id="analysisUsable">—</b></div><div class="summary-chip"><span class="mini" id="analysisStaleLabel">Stale</span><b id="analysisStale">—</b></div></div><div class="notice" id="analysisDisclaimer">Analysis only · No real-money order execution. Missing or stale data is not a trade signal.</div></section></div><div id="hub-markets" class="section-title"><div><div class="label">GLOBAL CONTEXT</div><h2>ATLAS Market Intelligence Boards</h2></div><button class="btn" id="refreshBoards">Refresh</button></div><div class="grid split"><section class="card"><div class="board-head"><div><div class="label">Wall Street Board · Context only</div><div class="updated" id="boardUpdated">—</div></div><span class="tag" id="breadth">—</span></div><div class="board-summary"><div class="summary-chip"><span class="mini">Breadth</span><b id="breadthValue">—</b></div><div class="summary-chip"><span class="mini">Rising</span><b id="rising">—</b></div><div class="summary-chip"><span class="mini">Falling</span><b id="falling">—</b></div><div class="summary-chip"><span class="mini">Tracked</span><b id="tracked">—</b></div><div class="summary-chip"><span class="mini">Usable</span><b id="usable">—</b></div><div class="summary-chip"><span class="mini">Stale</span><b id="stale">—</b></div></div><div id="marketBoard"></div></section><section class="card"><div class="board-head"><div><div class="label">Financial News · Context only</div><div class="updated" id="newsUpdated">—</div></div><span class="tag">AI</span></div><div id="headlines"></div></section></div><div class="notice" id="disclaimer">LIVE DEMO telemetry. ATLAS simulated demo execution is active; real-money trading is off.</div></div><script src="/assets/atlas-news.js"></script><script>function el(i){return document.getElementById(i)}function esc(v){return String(v==null?'':v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}function money(v,c){return v==null?'PRIVATE':Number(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+(c?' '+c:'')}function tone(v){return Number(v)>=0?'green':'red'}function ar(){try{return(localStorage.getItem('atlas-language')||document.documentElement.lang||'ar')==='ar'}catch(e){return document.documentElement.lang!=='en'}}function symbol(v){return'<bdi class="atlas-symbol" dir="ltr">'+esc(v)+'</bdi>'}function dt(v){if(!v)return'No quote time';try{return new Date(v).toLocaleString()}catch(e){return v}}function signalRow(x){return'<div class="row"><div><b>'+symbol(x.canonical_symbol||x.symbol)+'</b><div class="mini">'+esc(x.asset_class)+' · '+symbol(x.symbol)+'</div></div><div><span class="tag">'+esc(x.decision.bias)+'</span><div class="mini">'+esc(x.decision.decision)+'</div></div><div><b>'+Number(x.decision.score||0).toFixed(1)+'</b></div><div><b>'+Number(x.quality.execution_confidence||0).toFixed(1)+'%</b></div><div><b>'+Number(x.opportunity_score||0).toFixed(0)+'</b></div></div>'}let atlasStateInFlight=null;function fetchAtlasState(){if(!atlasStateInFlight){atlasStateInFlight=fetch('/dashboard/atlas',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('ATLAS data unavailable');return r.json()}).finally(()=>{atlasStateInFlight=null})}return atlasStateInFlight}async function refresh(){try{let d=await fetchAtlasState(),a=d.account||{};el('status').textContent=d.verified_live_account?'VERIFIED LIVE':'ONLINE';el('accountType').textContent=a.account_type||'—';el('equity').textContent=money(a.equity,a.currency);el('balance').textContent=money(a.balance,a.currency);el('floating').textContent=money(d.floating_position_pnl,a.currency);el('floating').className='big '+tone(d.floating_position_pnl);el('openPositions').textContent=d.open_positions||0;el('execution').textContent=d.services.execution_gate;el('brokerAccount').innerHTML='<div class="pos"><span>'+esc(a.label)+'</span><b>'+esc(a.login)+'</b><span>'+esc(a.server)+'</span><b>1:'+esc(a.leverage||'—')+'</b></div>';el('signals').innerHTML=(d.symbols||[]).map(signalRow).join('')||'<div class="empty">No markets available.</div>';el('positions').innerHTML=(d.positions||[]).map(p=>'<div class="pos"><div>'+symbol(p.symbol)+'<div class="mini">'+esc(p.direction)+'</div></div><div>'+p.volume+'</div><div>'+p.price_open+'</div><div class="'+tone(p.profit)+'"><b>'+Number(p.profit||0).toFixed(2)+'</b></div></div>').join('')||'<div class="empty">No open positions.</div>';el('disclaimer').textContent=d.disclaimer}catch(e){el('status').textContent='OFFLINE'}}let briefingRequest=0;async function refreshBriefing(){const request=++briefingRequest,language=ar()?'ar':'en';el('boardUpdated').textContent='Refreshing…';el('newsUpdated').textContent='Refreshing…';try{let r=await fetch('/dashboard/market-briefing?language='+language,{cache:'no-store'}),d=await r.json();if(request!==briefingRequest)return;if(!r.ok)throw Error();let m=d.market_analysis||{};el('breadth').textContent=m.breadth||'—';el('breadthValue').textContent=m.breadth||'—';el('rising').textContent=m.rising??'—';el('falling').textContent=m.falling??'—';el('tracked').textContent=m.tracked??'—';el('usable').textContent=m.usable??'—';el('stale').textContent=m.stale??'—';el('boardUpdated').textContent='Updated · '+dt(d.as_of);el('newsUpdated').textContent='Updated · '+dt(d.as_of);el('marketBoard').innerHTML=(d.market_board||[]).map(x=>'<div class="market"><div><b>'+esc(x.label)+'</b><div class="mini">'+symbol(x.symbol)+' · '+esc(x.category)+'</div><div class="quote-time">Quote · '+esc(dt(x.quote_time))+'</div></div><b>'+(x.price==null?'—':Number(x.price).toLocaleString())+'</b><b class="'+tone(x.change_percent)+'">'+(x.change_percent==null?'—':Number(x.change_percent).toFixed(2)+'%')+'</b><div><span class="freshness '+esc(x.freshness||'UNKNOWN')+'">'+esc(x.freshness||'UNKNOWN')+'</span><div class="mini" style="margin-top:5px">'+esc(x.direction||'UNAVAILABLE')+'</div></div></div>').join('')||'<div class="empty">Market data temporarily unavailable.</div>';AtlasNews.render(el('headlines'),d.headlines||[],language)}catch(e){if(request!==briefingRequest)return;el('boardUpdated').textContent='OFFLINE';el('newsUpdated').textContent='OFFLINE';el('marketBoard').innerHTML='<div class="empty">Market board unavailable.</div>';el('headlines').innerHTML='<div class="empty">Headlines unavailable.</div>'}}window.refreshBriefing=refreshBriefing;el('refreshAtlas').onclick=refresh;el('refreshBoards').onclick=refreshBriefing;el('refreshAll').onclick=()=>Promise.allSettled([refresh(),refreshBriefing(),window.refreshAnalysis()]);window.addEventListener('atlas-language-change',refreshBriefing);refresh();refreshBriefing();setInterval(refresh,5000);setInterval(refreshBriefing,60000);</script><script>(function(){
const E=id=>document.getElementById(id);
const safe=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy={
 heading:['Market Analysis','تحليل السوق'],
 signals:['Multi-Timeframe Signals','إشارات متعددة الأطر الزمنية'],
 context:['Market Breadth & Risk Context','اتساع السوق وسياق المخاطر'],
 breadth:['Breadth','اتساع السوق'],
 usable:['Usable','بيانات صالحة'],
 stale:['Stale','بيانات قديمة'],
 disclaimer:['Analysis only · No real-money order execution. Missing or stale data is not a trade signal.','تحليل للعرض فقط · لا تنفيذ لأوامر بأموال حقيقية. البيانات المفقودة أو القديمة ليست إشارة تداول.'],
 refresh:['Refresh Analysis','تحديث التحليل'],
 loading:['Loading analysis…','جارٍ تحميل التحليل…'],
 source:['Source: ATLAS /dashboard/atlas','المصدر: ATLAS /dashboard/atlas'],
 checking:['Briefing checked','آخر فحص للإحاطة'],
 decision:['Decision','القرار'],
 bias:['Bias','الاتجاه'],
 confidence:['Confidence','الثقة'],
 unavailable:['Analysis unavailable. No current values shown.','التحليل غير متاح. لا تُعرض قيم حالية.'],
 empty:['No verified signals available.','لا توجد إشارات موثّقة متاحة.'],
 waiting:['WAITING','بانتظار البيانات'],
 fresh:['FRESH','حديثة'],
 delayed:['DELAYED','متأخرة'],
 staleStatus:['STALE','قديمة'],
 unavailableStatus:['UNAVAILABLE','غير متاح']
};
const tx=key=>copy[key][ar()?1:0];
function translateAnalysis(){
 E('analysisHeading').textContent=tx('heading');
 E('analysisSignalsHeading').textContent=tx('signals');
 E('analysisContextHeading').textContent=tx('context');
 E('analysisBreadthLabel').textContent=tx('breadth');
 E('analysisUsableLabel').textContent=tx('usable');
 E('analysisStaleLabel').textContent=tx('stale');
 E('analysisDisclaimer').textContent=tx('disclaimer');
 E('refreshAnalysis').textContent=tx('refresh');
}
function resetAnalysis(){
 E('analysisBreadth').textContent='—';
 E('analysisUsable').textContent='—';
 E('analysisStale').textContent='—';
 E('analysisTime').textContent=tx('source');
 E('analysisSignals').innerHTML='<div class="empty">'+safe(tx('unavailable'))+'</div>';
 E('analysisStatus').textContent=tx('unavailableStatus');
 E('analysisStatus').className='freshness UNAVAILABLE';
}
function statusFor(brief,m){
 const usable=Number(m.usable)||0,stale=Number(m.stale)||0,status=String(brief.status||'UNKNOWN').toUpperCase();
 const delayed=Array.isArray(brief.market_board)&&brief.market_board.some(item=>String(item.freshness||item.market_state||'').toUpperCase()==='DELAYED');
 if(status!=='ONLINE')return usable>0?'DELAYED':stale>0?'STALE':'UNAVAILABLE';
 if(stale>0)return usable>0?'DELAYED':'STALE';
 if(delayed)return 'DELAYED';
 return usable>0?'FRESH':'UNAVAILABLE';
}
let analysisInFlight=null;
async function loadAnalysis(){
 if(analysisInFlight)return analysisInFlight;
 translateAnalysis();
 E('analysisStatus').textContent=tx('waiting');
 E('analysisStatus').className='freshness UNKNOWN';
 E('analysisSignals').innerHTML='<div class="empty">'+safe(tx('loading'))+'</div>';
 const task=(async()=>{
  try{
   const language=ar()?'ar':'en';
   const [state,brief]=await Promise.all([
    fetchAtlasState(),
    fetch('/dashboard/market-briefing?language='+language,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Briefing unavailable');return r.json()})
   ]);
   const m=brief.market_analysis||{},signals=Array.isArray(state.symbols)?state.symbols:[];
   const freshness=statusFor(brief,m),statusLabel={FRESH:'fresh',DELAYED:'delayed',STALE:'staleStatus',UNAVAILABLE:'unavailableStatus'}[freshness];
   E('analysisBreadth').textContent=m.breadth||'—';
   E('analysisUsable').textContent=m.usable??'—';
   E('analysisStale').textContent=m.stale??'—';
   E('analysisTime').textContent=tx('checking')+': '+safe(dt(brief.as_of));
   E('analysisSignals').innerHTML=signals.length?signals.slice(0,12).map(x=>{
    const d=x.decision||{},q=x.quality||{},t=x.timeframes||{},confidence=Number(q.execution_confidence);
    const confidenceText=Number.isFinite(confidence)?confidence.toFixed(1)+'%':'—';
    const frames=Object.entries(t).map(([tf,v])=>safe(tf)+': '+safe((v||{}).trend||(v||{}).signal)).join(' · ');
    return '<div class="analysis-row"><div><b>'+safe(x.canonical_symbol||x.symbol)+'</b><div class="mini">'+safe(x.asset_class)+'</div></div><div class="analysis-value"><span class="mini">'+safe(tx('decision'))+': </span><b>'+safe(d.decision)+'</b><div class="mini">'+safe(tx('bias'))+': '+safe(d.bias)+'</div></div><div class="analysis-value"><span class="mini">'+safe(tx('confidence'))+': </span><b>'+confidenceText+'</b></div><div class="mini analysis-timeframes">'+frames+'</div></div>'
   }).join(''):'<div class="empty">'+safe(tx('empty'))+'</div>';
   E('analysisStatus').textContent=tx(statusLabel);
   E('analysisStatus').className='freshness '+freshness;
  }catch(e){resetAnalysis()}
 })();
 analysisInFlight=task;
 try{return await task}finally{analysisInFlight=null}
}
E('refreshAnalysis').addEventListener('click',loadAnalysis);
window.refreshAnalysis=loadAnalysis;
window.addEventListener('atlas-language-change',()=>{translateAnalysis();loadAnalysis()});
translateAnalysis();
loadAnalysis();
setInterval(loadAnalysis,60000);
})();</script></body></html>'''


