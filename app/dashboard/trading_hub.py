"""Presentation-only enhancement for the canonical ATLAS customer dashboard."""

HUB_STYLE = r"""
<style id="atlas-hub-style">
:root{--hub-orange:#ff7a1a;--hub-metal:#9aa8bb;--hub-deep:#05080d;--hub-panel:#0b121c}
body{font-family:Inter,"Noto Sans Arabic","Segoe UI",Tahoma,Arial,sans-serif;background:radial-gradient(circle at 80% 0,#ff7a1a12,transparent 28%),linear-gradient(145deg,#05070b,#0a111a 55%,#05070b);letter-spacing:.01em}
.atlas-hub-shell{max-width:1500px;margin:18px auto;padding:0 18px;position:relative;z-index:5}.atlas-hub-brand{border:1px solid #8190a455;border-radius:24px;padding:22px;background:linear-gradient(145deg,#111b28e8,#070b12f2);box-shadow:inset 0 1px 0 #ffffff18,0 24px 70px #0008,0 0 36px #ff7a1a0d;display:flex;justify-content:space-between;gap:20px;align-items:center}.atlas-hub-kicker{font-size:11px;font-weight:900;letter-spacing:.18em;color:var(--hub-orange)}.atlas-hub-title{font-size:clamp(34px,5vw,68px);font-weight:950;line-height:.95;margin:7px 0 0;background:linear-gradient(180deg,#fff,#b9c1cc);-webkit-background-clip:text;color:transparent;text-shadow:0 10px 30px #000}.atlas-hub-descriptor{font-size:clamp(9px,1.2vw,18px);font-weight:900;letter-spacing:.18em;color:#c7d0dc;margin-top:2px}.atlas-hub-parent{font-size:12px;font-weight:900;letter-spacing:.16em;color:var(--hub-orange);margin-top:28px}.atlas-hub-sub{color:#aab5c5;font-size:13px;margin-top:7px}.atlas-hub-status{display:flex;align-items:center;gap:8px;border:1px solid #ff7a1a55;border-radius:999px;padding:10px 14px;background:#21160dcc;box-shadow:inset 0 1px 0 #ffffff12}.atlas-hub-status-dot{width:9px;height:9px;border-radius:50%;background:#ff7a1a;box-shadow:none}.atlas-hub-nav{display:flex;gap:9px;overflow-x:auto;padding:12px 2px 4px;scrollbar-width:none}.atlas-hub-nav::-webkit-scrollbar{display:none}.atlas-hub-nav a,.atlas-3d,.btn{min-height:44px;display:inline-flex;align-items:center;justify-content:center;border:1px solid #8493a766;border-radius:12px;padding:9px 15px;text-decoration:none;color:inherit;font-weight:850;background:linear-gradient(180deg,#182331,#0b1119);box-shadow:inset 0 1px 0 #ffffff20,inset 0 -2px 0 #0008,0 8px 18px #0007;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}.atlas-hub-nav a:hover,.atlas-3d:hover,.btn:hover{border-color:#ff7a1a99;box-shadow:inset 0 1px 0 #ffffff2b,inset 0 -2px 0 #0008,0 10px 25px #0009,0 0 20px #ff7a1a22;transform:translateY(-2px)}.atlas-hub-nav a:active,.atlas-3d:active,.btn:active{transform:translateY(1px);box-shadow:inset 0 3px 8px #000b,0 3px 8px #0008}.atlas-hub-nav a:focus-visible,.atlas-3d:focus-visible,.btn:focus-visible{outline:3px solid #ff7a1a55;outline-offset:2px}.card{background:linear-gradient(145deg,#101923ed,#080d14f2)!important;border-color:#60708766!important;box-shadow:inset 0 1px 0 #ffffff0e,0 16px 40px #0005!important}.section-title{scroll-margin-top:90px}.demo-session{margin-top:22px!important;box-shadow:inset 0 1px 0 #ffffff10,0 18px 45px #0006!important}.demo-session .demo-title{font-size:clamp(20px,3vw,30px)}
html[dir=rtl] body{font-family:"Noto Sans Arabic",Tahoma,"Segoe UI",Arial,sans-serif;letter-spacing:0;line-height:1.8}html[dir=rtl] .atlas-hub-brand,html[dir=rtl] .atlas-hub-nav{direction:rtl}html[dir=rtl] .atlas-hub-title{letter-spacing:0}html[dir=rtl] .atlas-hub-kicker{letter-spacing:.08em}.atlas-tech-token{direction:ltr;unicode-bidi:isolate;display:inline-block}
@media(max-width:700px){.atlas-hub-shell{padding:0 12px;margin-top:12px}.atlas-hub-brand{padding:18px;border-radius:20px;align-items:flex-start;flex-direction:column}.atlas-hub-nav a{white-space:nowrap;min-height:44px}.atlas-hub-status{font-size:12px}.card{border-radius:18px!important}.demo-metrics,.performance-grid{grid-template-columns:1fr 1fr!important}.atlas-hub-title{font-size:34px}}
@media(max-width:430px){.demo-metrics,.performance-grid{grid-template-columns:1fr!important}.atlas-hub-nav{margin-inline:-4px}}

[hidden]{display:none!important}
.atlas-account{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;margin-top:20px;scroll-margin-top:24px}
.atlas-account-controls{min-width:0}.atlas-account-controls p{line-height:1.7;overflow-wrap:anywhere}
.atlas-account summary{cursor:pointer;min-height:44px;display:flex;align-items:center}
.atlas-hub-nav{scrollbar-width:thin;scrollbar-color:#ff7a1a #111b28}.atlas-hub-nav::-webkit-scrollbar{display:block;height:4px}
.grid>*{min-width:0}.big{overflow-wrap:anywhere}.btn:disabled{opacity:.55;cursor:wait}
html[data-theme=light] .card{background:#fff!important;color:#152033;border-color:#ccd2dc!important}
html[data-theme=light] .atlas-hub-brand,html[data-theme=light] .hero{background:#f1eee7;color:#152033}
html[data-theme=light] .atlas-hub-title{background:none;color:#152033;text-shadow:none}
html[data-theme=light] .atlas-hub-descriptor,html[data-theme=light] .atlas-hub-sub{color:#475569}
html[data-theme=light] .atlas-hub-nav a,html[data-theme=light] .btn{background:#fff;color:#152033;box-shadow:0 3px 10px #17233612}
html[data-theme=light] .atlas-hub-status{background:#fff6e9;border-color:#b5480066;color:#703900}
@media(max-width:700px){.atlas-account{grid-template-columns:1fr;gap:12px}.shell{padding:12px}.section-title{align-items:flex-start}.section-title h2{font-size:21px}.atlas-account-controls .btn{width:100%}select,input{max-width:100%;font-size:16px}}
@media(prefers-reduced-motion:reduce){.atlas-hub-nav a,.atlas-3d,.btn{transition:none;transform:none!important}}

/* Shared light dashboard design tokens: aligned with ATLAS council and MT5 cards. */
html[data-theme=light]{
  --atlas-surface:#ffffff;--atlas-surface-muted:#eaf0fa;--atlas-page:#f5f7fd;
  --atlas-ink:#263149;--atlas-secondary:#64718a;--atlas-border:#d7dfec;
  --atlas-primary:#4c60af;--atlas-loss:#bd4b70;--atlas-positive:#087b55;
  color-scheme:light;
}
html[data-theme=light] body{
  background:radial-gradient(circle at 75% 4%,#e7eefc 0,transparent 40%),
    linear-gradient(165deg,#f9fbff,#f0f4fc 58%,#f8faff)!important;
  color:var(--atlas-ink)!important;
}
html[data-theme=light] .card,
html[data-theme=light] .hero,
html[data-theme=light] .demo-session,
html[data-theme=light] .atlas-account,
html[data-theme=light] .atlas-plans{
  background:var(--atlas-surface)!important;color:var(--atlas-ink)!important;
  border:1px solid var(--atlas-border)!important;border-radius:24px!important;
  box-shadow:0 14px 36px #27395e12,0 3px 9px #27395e08!important;
}
html[data-theme=light] .atlas-hub-brand{
  background:linear-gradient(135deg,#fff,#eaf0fb)!important;
  color:var(--atlas-ink)!important;border-color:var(--atlas-border)!important;
  box-shadow:0 16px 36px #27395e12!important;
}
html[data-theme=light] .atlas-hub-title{color:var(--atlas-ink)!important}
html[data-theme=light] .big,
html[data-theme=light] .summary-chip b{color:var(--atlas-primary)}
html[data-theme=light] .red{color:var(--atlas-loss)!important}
html[data-theme=light] .green{color:var(--atlas-positive)!important}
html[data-theme=light] .mini,
html[data-theme=light] .label,
html[data-theme=light] .sub,
html[data-theme=light] .updated{color:var(--atlas-secondary)!important}
html[data-theme=light] .summary-chip,
html[data-theme=light] .atlas-hub-status{
  background:var(--atlas-surface-muted)!important;border-color:var(--atlas-border)!important;
  color:var(--atlas-ink)!important;
}
html[data-theme=light] .row,
html[data-theme=light] .market,
html[data-theme=light] .pos,
html[data-theme=light] .story{border-bottom-color:var(--atlas-border)!important}
html[data-theme=light] .atlas-hub-nav a,
html[data-theme=light] .btn,
html[data-theme=light] select,
html[data-theme=light] input{
  background:linear-gradient(#fff,#f2f5fc)!important;color:var(--atlas-ink)!important;
  border:1px solid var(--atlas-border)!important;box-shadow:0 4px 12px #253a6310!important;
}
html[data-theme=light] .btn.primary{background:var(--atlas-primary)!important;color:#fff!important}
html[data-theme=light] .story{color:var(--atlas-ink)!important}
html[data-theme=light] .story:hover{background:#f5f8ff}
html[data-theme=light] .notice{background:#edf2fd!important;border-color:var(--atlas-primary)!important;color:var(--atlas-ink)!important}
html[data-theme=light] .atlas-hub-nav a:focus-visible,
html[data-theme=light] .btn:focus-visible{outline:3px solid #526bb388;outline-offset:2px}
@media(max-width:700px){
  .atlas-hub-shell,.shell{max-width:100%;min-width:0}
  .card,.hero{min-width:0}
  .row,.market,.pos{overflow-wrap:anywhere}
  .atlas-hub-nav{overscroll-behavior-inline:contain}
  .atlas-hub-nav a{flex-shrink:0}
  .story b{overflow-wrap:anywhere}
}

/* ATLAS dimensional surfaces: subtle, responsive, and accessible. */
html[data-theme=light] .card,
html[data-theme=light] .hero,
html[data-theme=light] .demo-session,
html[data-theme=light] .atlas-account,
html[data-theme=light] .atlas-plans{
  position:relative;
  background:linear-gradient(148deg,#fff 0%,#fbfcff 48%,#eaf0fa 100%)!important;
  border:1px solid #dbe3f1!important;
  box-shadow:inset 1px 1px 0 #fff, inset -1px -1px 0 #dce4f3,
    0 3px 0 #d3dced,0 9px 14px #263b6220,0 25px 44px #263b6215!important;
  transform:translateZ(0);
}
html[data-theme=light] .summary-chip,
html[data-theme=light] .atlas-hub-status{
  background:linear-gradient(145deg,#f6f9ff,#e3eaf8)!important;
  box-shadow:inset 1px 1px 1px #fff, inset -2px -2px 4px #cad5e9,
    0 6px 12px #253a6316!important;
  border-radius:15px;
}
html[data-theme=light] .atlas-hub-nav a,
html[data-theme=light] .btn,
html[data-theme=light] select{
  background:linear-gradient(155deg,#fff 5%,#edf2fc 95%)!important;
  box-shadow:inset 1px 1px 0 #fff,0 3px 0 #d0d9e9,0 7px 13px #24385e24!important;
  border-radius:13px;
  transition:transform .18s ease,box-shadow .18s ease;
}
@media(hover:hover) and (prefers-reduced-motion:no-preference){
  html[data-theme=light] .atlas-hub-nav a:hover,
  html[data-theme=light] .btn:hover{transform:translateY(-2px);
    box-shadow:inset 1px 1px 0 #fff,0 5px 0 #cbd5e7,0 12px 20px #24385e2b!important}
}
html[data-theme=light] .atlas-hub-nav a:active,
html[data-theme=light] .btn:active{transform:translateY(2px);
  box-shadow:inset 1px 1px 0 #fff,0 1px 2px #24385e22!important}
html[data-theme=light] .red{ text-shadow:0 1px 0 #fff; }
html[data-theme=light] .big{ text-shadow:0 2px 1px #fff,0 4px 8px #425b9a1b; }
@media(prefers-reduced-motion:reduce){
  html[data-theme=light] .atlas-hub-nav a,
  html[data-theme=light] .btn{transition:none!important;transform:none!important}
}
</style>
"""

HUB_HEADER = r"""
<div class="atlas-hub-shell" id="hub-overview">
  <header class="atlas-hub-brand">
    <div>
      <div class="atlas-hub-kicker"><span class="atlas-tech-token">CUSTOMER TRADING INTERFACE</span></div>
      <div class="atlas-hub-title"><span class="atlas-tech-token">ATLAS</span></div>
      <div class="atlas-hub-descriptor"><span class="atlas-tech-token">TRADING INTELLIGENCE</span></div>
      <div class="atlas-hub-parent"><span class="atlas-tech-token">JUST AI</span></div>
      <div class="atlas-hub-sub" data-hub-en="Your unified FxPro MT5 demo cockpit for markets, account telemetry, analysis and risk context." data-hub-ar="واجهة موحّدة لحساب FxPro MT5 التجريبي والأسواق والتحليل وسياق المخاطر.">Unified market intelligence, monitoring and risk context.</div>
    </div>
    <div class="atlas-hub-status"><span class="atlas-hub-status-dot"></span><span data-hub-en="FxPro MT5 workspace" data-hub-ar="مساحة عمل FxPro MT5">FxPro MT5 workspace</span></div>
  </header>
  <nav class="atlas-hub-nav" aria-label="Trading Hub">
    <a class="atlas-3d" href="#account" data-hub-en="Sign in" data-hub-ar="تسجيل الدخول">Sign in</a>
    <a class="atlas-3d" href="#hub-overview" data-hub-en="Overview" data-hub-ar="الرئيسية">Overview</a>
    <a class="atlas-3d" href="#hub-account" data-hub-en="Account" data-hub-ar="الحساب">Account</a>
    <a class="atlas-3d" href="#hub-markets" data-hub-en="Market Analysis" data-hub-ar="تحليل الأسواق">Market Analysis</a>
    <a class="atlas-3d" href="#demo-session" data-hub-en="Live Demo" data-hub-ar="تجريبي مباشر">Live Demo</a>
    <a class="atlas-3d" href="#plans" data-hub-en="Plans" data-hub-ar="الاشتراكات">Plans</a>
  </nav>
</div>
"""

HUB_SCRIPT = r"""
<script id="atlas-hub-script">
(()=>{
const arMap={
'LIVE DEMO':'تجريبي مباشر','ATLAS Live Demo Trading':'التداول التجريبي المباشر من ATLAS','Real-time MT5 demo quotes · ATLAS simulated demo execution · no real-money orders':'أسعار MT5 تجريبية مباشرة · تنفيذ تجريبي محاكى من ATLAS · لا تداول بأموال حقيقية','Open Demo Trades':'الصفقات التجريبية المفتوحة','Closed Trades':'الصفقات التجريبية المغلقة','Review Target':'هدف المراجعة','Profit Factor':'معامل الربح','Expectancy':'القيمة المتوقعة','Drawdown / Risk':'التراجع / المخاطر','Latest Demo Events':'آخر أحداث التداول التجريبي','Real-Money Readiness Gate':'بوابة الجاهزية للتداول بأموال حقيقية','Drawdown Alert':'تنبيه التراجع','Last update:':'آخر تحديث:','DEMO ANALYTICS':'تحليلات التداول التجريبي','Performance Center':'مركز الأداء','Risk-normalized live-demo results · simulated, not real-money P/L':'نتائج تجريبية مباشرة مطبّعة حسب المخاطر · محاكاة وليست أرباحاً أو خسائر بأموال حقيقية','Asset':'الأصل','Timeframe':'الإطار الزمني','All Assets':'كل الأصول','All Timeframes':'كل الأطر الزمنية','Win Rate':'معدل النجاح','Cumulative P/L':'الربح/الخسارة التراكمية','Best Asset':'أفضل أصل','Worst Asset':'أضعف أصل','Equity Curve · Risk Normalized':'منحنى الأداء · مطبّع حسب المخاطر','Recent Closed Trades':'أحدث الصفقات التجريبية المغلقة','No demo event recorded in the latest cycle.':'لم يُسجّل حدث تداول تجريبي في آخر دورة.','Loading session activity…':'جارٍ تحميل نشاط الجلسة…','Evaluating demo evidence…':'جارٍ تقييم أدلة التداول التجريبي…','Waiting for paper-risk evidence…':'بانتظار أدلة مخاطر التداول التجريبي…','no real-money orders':'لا أوامر بأموال حقيقية','CONNECTING':'جارٍ الاتصال','NOT_STARTED':'لم يبدأ','STALE':'بيانات قديمة','NORMAL':'طبيعي','WATCH':'مراقبة','HIGH':'مرتفع'};
const reverse=new Map(Object.entries(arMap).map(([en,ar])=>[ar,en]));
function lang(){return document.documentElement.lang==='ar'?'ar':'en'}
function localizeNode(node){if(!node||node.nodeType!==3)return;const raw=node.nodeValue.trim();if(!raw)return;const en=reverse.get(raw)||raw;if(arMap[en]){const out=lang()==='ar'?arMap[en]:en;if(raw!==out)node.nodeValue=node.nodeValue.replace(raw,out)}else if(raw.startsWith('Last update:')){node.nodeValue=(lang()==='ar'?'آخر تحديث:':'Last update:')+raw.split(':').slice(1).join(':')}}
function apply(){document.querySelectorAll('[data-hub-en]').forEach(el=>{el.textContent=lang()==='ar'?el.dataset.hubAr:el.dataset.hubEn});const root=document.getElementById('demo-session');if(root){const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(w.nextNode())localizeNode(w.currentNode)}}
let queued=false;const observer=new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;observer.disconnect();apply();observer.observe(document.body,{subtree:true,childList:true,characterData:true})})});observer.observe(document.body,{subtree:true,childList:true,characterData:true});window.addEventListener('atlas-language-change',apply);apply();
})();
</script>
"""


def enhance_atlas_html(html: str) -> str:
    """Add the approved Trading Hub shell without changing backend/data semantics."""
    if "atlas-hub-style" in html:
        return html
    html = html.replace("</head>", HUB_STYLE + "</head>")
    html = html.replace("<body>", "<body>" + HUB_HEADER, 1)
    return html.replace("</body>", HUB_SCRIPT + "</body>")
