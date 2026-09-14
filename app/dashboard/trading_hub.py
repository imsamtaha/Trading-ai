"""Presentation-only enhancement for the canonical ATLAS customer dashboard."""

HUB_STYLE = r"""
<style id="atlas-hub-style">
:root{--hub-orange:#ff7a1a;--hub-metal:#9aa8bb;--hub-deep:#05080d;--hub-panel:#0b121c}
body{font-family:Inter,"Noto Sans Arabic","Segoe UI",Tahoma,Arial,sans-serif;background:radial-gradient(circle at 80% 0,#ff7a1a12,transparent 28%),linear-gradient(145deg,#05070b,#0a111a 55%,#05070b);letter-spacing:.01em}
.atlas-hub-shell{max-width:1500px;margin:18px auto;padding:0 18px;position:relative;z-index:5}.atlas-hub-brand{border:1px solid #8190a455;border-radius:24px;padding:22px;background:linear-gradient(145deg,#111b28e8,#070b12f2);box-shadow:inset 0 1px 0 #ffffff18,0 24px 70px #0008,0 0 36px #ff7a1a0d;display:flex;justify-content:space-between;gap:20px;align-items:center}.atlas-hub-kicker{font-size:11px;font-weight:900;letter-spacing:.28em;color:var(--hub-orange)}.atlas-hub-title{font-size:clamp(30px,5vw,64px);font-weight:950;line-height:1;margin:7px 0;background:linear-gradient(180deg,#fff,#b9c1cc);-webkit-background-clip:text;color:transparent;text-shadow:0 10px 30px #000}.atlas-hub-sub{color:#aab5c5;font-size:13px}.atlas-hub-status{display:flex;align-items:center;gap:8px;border:1px solid #3adf8c55;border-radius:999px;padding:10px 14px;background:#07130dcc;box-shadow:inset 0 1px 0 #ffffff12}.atlas-hub-status-dot{width:9px;height:9px;border-radius:50%;background:#39d98a;box-shadow:0 0 16px #39d98a}.atlas-hub-nav{display:flex;gap:9px;overflow-x:auto;padding:12px 2px 4px;scrollbar-width:none}.atlas-hub-nav::-webkit-scrollbar{display:none}.atlas-hub-nav a,.atlas-3d,.btn{min-height:44px;display:inline-flex;align-items:center;justify-content:center;border:1px solid #8493a766;border-radius:12px;padding:9px 15px;text-decoration:none;color:inherit;font-weight:850;background:linear-gradient(180deg,#182331,#0b1119);box-shadow:inset 0 1px 0 #ffffff20,inset 0 -2px 0 #0008,0 8px 18px #0007;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}.atlas-hub-nav a:hover,.atlas-3d:hover,.btn:hover{border-color:#ff7a1a99;box-shadow:inset 0 1px 0 #ffffff2b,inset 0 -2px 0 #0008,0 10px 25px #0009,0 0 20px #ff7a1a22;transform:translateY(-2px)}.atlas-hub-nav a:active,.atlas-3d:active,.btn:active{transform:translateY(1px);box-shadow:inset 0 3px 8px #000b,0 3px 8px #0008}.atlas-hub-nav a:focus-visible,.atlas-3d:focus-visible,.btn:focus-visible{outline:3px solid #ff7a1a55;outline-offset:2px}.card{background:linear-gradient(145deg,#101923ed,#080d14f2)!important;border-color:#60708766!important;box-shadow:inset 0 1px 0 #ffffff0e,0 16px 40px #0005!important}.section-title{scroll-margin-top:90px}.demo-session{margin-top:22px!important;box-shadow:inset 0 1px 0 #ffffff10,0 18px 45px #0006!important}.demo-session .demo-title{font-size:clamp(20px,3vw,30px)}
html[dir=rtl] body{font-family:"Noto Sans Arabic",Tahoma,"Segoe UI",Arial,sans-serif;letter-spacing:0;line-height:1.8}html[dir=rtl] .atlas-hub-brand,html[dir=rtl] .atlas-hub-nav{direction:rtl}html[dir=rtl] .atlas-hub-title{letter-spacing:0}html[dir=rtl] .atlas-hub-kicker{letter-spacing:.08em}.atlas-tech-token{direction:ltr;unicode-bidi:isolate;display:inline-block}
@media(max-width:700px){.atlas-hub-shell{padding:0 12px;margin-top:12px}.atlas-hub-brand{padding:18px;border-radius:20px;align-items:flex-start;flex-direction:column}.atlas-hub-nav a{white-space:nowrap;min-height:44px}.atlas-hub-status{font-size:12px}.card{border-radius:18px!important}.demo-metrics,.performance-grid{grid-template-columns:1fr 1fr!important}.atlas-hub-title{font-size:34px}}
@media(max-width:430px){.demo-metrics,.performance-grid{grid-template-columns:1fr!important}.atlas-hub-nav{margin-inline:-4px}}
</style>
"""

HUB_HEADER = r"""
<div class="atlas-hub-shell" id="hub-overview">
  <header class="atlas-hub-brand">
    <div>
      <div class="atlas-hub-kicker"><span class="atlas-tech-token">JUST AI · ATLAS ULTIMATE</span></div>
      <div class="atlas-hub-title"><span class="atlas-tech-token">TRADING HUB</span></div>
      <div class="atlas-hub-sub" data-hub-en="Unified market intelligence, monitoring and risk context." data-hub-ar="مركز موحّد لذكاء الأسواق والمراقبة وسياق المخاطر.">Unified market intelligence, monitoring and risk context.</div>
    </div>
    <div class="atlas-hub-status"><span class="atlas-hub-status-dot"></span><span data-hub-en="Read-only intelligence" data-hub-ar="ذكاء أسواق للقراءة فقط">Read-only intelligence</span></div>
  </header>
  <nav class="atlas-hub-nav" aria-label="Trading Hub">
    <a class="atlas-3d" href="#hub-overview" data-hub-en="Overview" data-hub-ar="الرئيسية">Overview</a>
    <a class="atlas-3d" href="#hub-account" data-hub-en="Account" data-hub-ar="الحساب">Account</a>
    <a class="atlas-3d" href="#hub-markets" data-hub-en="Markets & News" data-hub-ar="الأسواق والأخبار">Markets & News</a>
    <a class="atlas-3d" href="#demo-session" data-hub-en="Paper Demo" data-hub-ar="التداول التجريبي">Paper Demo</a>
    <a class="atlas-3d" href="#plans" data-hub-en="Plans" data-hub-ar="الاشتراكات">Plans</a>
  </nav>
</div>
"""

HUB_SCRIPT = r"""
<script id="atlas-hub-script">
(()=>{
const arMap={
'FORWARD DEMO VALIDATION':'التحقق المتقدم من التداول التجريبي','ATLAS Demo Trading':'التداول التجريبي من ATLAS','MT5 market quotes · local paper ledger · subscriber execution isolated':'أسعار MT5 · سجل تداول ورقي محلي · تنفيذ المشتركين معزول','Open Paper Trades':'الصفقات التجريبية المفتوحة','Closed Trades':'الصفقات التجريبية المغلقة','Review Target':'هدف المراجعة','Profit Factor':'معامل الربح','Expectancy':'القيمة المتوقعة','Drawdown / Risk':'التراجع / المخاطر','Latest Demo Events':'آخر أحداث التداول التجريبي','Live Readiness Gate':'بوابة الجاهزية للتداول الحقيقي','Drawdown Alert':'تنبيه التراجع','Last update:':'آخر تحديث:','DEMO ANALYTICS':'تحليلات التداول التجريبي','Performance Center':'مركز الأداء','Risk-normalized paper results · not broker P/L':'نتائج تجريبية مطبّعة حسب المخاطر · ليست أرباحاً أو خسائر لدى الوسيط','Asset':'الأصل','Timeframe':'الإطار الزمني','All Assets':'كل الأصول','All Timeframes':'كل الأطر الزمنية','Win Rate':'معدل النجاح','Cumulative P/L':'الربح/الخسارة التراكمية','Best Asset':'أفضل أصل','Worst Asset':'أضعف أصل','Equity Curve · Risk Normalized':'منحنى الأداء · مطبّع حسب المخاطر','Recent Closed Paper Trades':'أحدث الصفقات التجريبية المغلقة','No demo event recorded in the latest cycle.':'لم يُسجّل حدث تداول تجريبي في آخر دورة.','Loading session activity…':'جارٍ تحميل نشاط الجلسة…','Evaluating demo evidence…':'جارٍ تقييم أدلة التداول التجريبي…','Waiting for paper-risk evidence…':'بانتظار أدلة مخاطر التداول التجريبي…','No broker orders':'لا أوامر للوسيط','CONNECTING':'جارٍ الاتصال','NOT_STARTED':'لم يبدأ','STALE':'بيانات قديمة','NORMAL':'طبيعي','WATCH':'مراقبة','HIGH':'مرتفع'};
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
    html = html.replace('class="section-title">LIVE ACCOUNT TELEMETRY', 'id="hub-account" class="section-title">LIVE ACCOUNT TELEMETRY')
    html = html.replace('class="section-title">GLOBAL CONTEXT', 'id="hub-markets" class="section-title">GLOBAL CONTEXT')
    return html.replace("</body>", HUB_SCRIPT + "</body>")
