from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/ui/preferences.js", include_in_schema=False)
def preferences_script():
    return Response(SCRIPT, media_type="application/javascript")


SCRIPT = r"""
(()=>{
const translations={
 'JUST AI · Unified Trading Intelligence':'JUST AI · منظومة موحّدة لذكاء التداول',
 'Markets':'الأسواق','Reader plans':'خطط الاشتراك','Plans':'خطط الاشتراك','Refresh All':'تحديث الكل','Refresh':'تحديث','Refreshing…':'جارٍ التحديث…','Updated':'تم التحديث',
 'CONNECTING':'جارٍ الاتصال','OFFLINE':'غير متصل','ONLINE':'متصل','VERIFIED LIVE':'حساب حقيقي تم التحقّق منه',
 'AI MARKET OBSERVATORY':'مرصد الأسواق بالذكاء الاصطناعي',
 'One intelligence layer.':'طبقة ذكاء واحدة.','Every market signal.':'لكل إشارة في السوق.',
 'Live read-only MT5 telemetry, multi-asset opportunity analysis, Wall Street context and financial headlines — consolidated into one ATLAS ULTIMATE command center.':'بيانات MT5 مباشرة للقراءة فقط، وتحليل فرص متعدد الأصول، وسياق وول ستريت، والأخبار المالية — مجمّعة في مركز قيادة ATLAS ULTIMATE واحد.',
 'Core':'النظام الأساسي','Live telemetry':'بيانات مباشرة','Engine':'المحرّك','Decision support':'دعم القرار','Coverage':'التغطية','Multi-Asset':'متعدد الأصول','Mode':'الوضع','Read Only':'للقراءة فقط','Execution isolated':'التنفيذ معزول',
 'LIVE ACCOUNT TELEMETRY':'بيانات الحساب المباشرة','Trading cockpit':'مركز مراقبة التداول',
 'Account Type':'نوع الحساب','Equity':'حقوق الحساب','Balance':'الرصيد','Floating P/L':'الربح والخسارة العائمان','Open Positions':'الصفقات المفتوحة','Execution Gate':'بوابة التنفيذ',
 'ATLAS ANALYTICS':'تحليلات ATLAS','Opportunity matrix & account state':'مصفوفة الفرص وحالة الحساب','ATLAS Opportunity Matrix':'مصفوفة فرص ATLAS','Verified Account':'الحساب المتحقّق منه',
 'GLOBAL CONTEXT':'السياق العالمي','Wall Street board & financial news':'لوحة وول ستريت والأخبار المالية','Wall Street Board · Context only':'لوحة وول ستريت · للسياق فقط','Financial News · Context only':'الأخبار المالية · للسياق فقط',
 'Read-only telemetry. Trading involves risk.':'بيانات للقراءة فقط. التداول ينطوي على مخاطر.',
 'Unified market intelligence interface. MT5 execution remains isolated from public subscriber access. Market information is decision-support context and does not guarantee outcomes.':'واجهة موحّدة لذكاء الأسواق. يبقى تنفيذ MT5 معزولاً عن وصول المشتركين. معلومات السوق مخصّصة لدعم القرار ولا تضمن النتائج.',
 'AI is for everyone.':'الذكاء الاصطناعي للجميع.',
 'No markets available.':'لا توجد أسواق متاحة.','No open positions.':'لا توجد صفقات مفتوحة.','Market data temporarily unavailable.':'بيانات السوق غير متاحة مؤقتاً.','Financial headlines temporarily unavailable.':'الأخبار المالية غير متاحة مؤقتاً.','Market board unavailable.':'لوحة السوق غير متاحة.','Headlines unavailable.':'الأخبار غير متاحة.',
 'score':'النتيجة','confidence':'الثقة','opportunity':'الفرصة','Context only':'للسياق فقط',
 'PRIVATE':'خاص','DEMO':'تجريبي','REAL':'حقيقي','UNKNOWN':'غير معروف','ENABLED':'مفعّل','DISABLED':'معطّل','WAIT':'انتظار','BUY':'شراء','SELL':'بيع','BULLISH':'صاعد','BEARISH':'هابط','NEUTRAL':'محايد','NO_TRADE':'لا صفقة',
 'ATLAS ULTIMATE ACCESS':'اشتراكات ATLAS ULTIMATE','Choose your intelligence level.':'اختر مستوى الذكاء المناسب لك.','Market Watch':'مراقبة الأسواق','ATLAS Signals':'إشارات ATLAS','Enterprise':'المؤسسات','Custom':'مخصّص','/ month':'/ شهرياً','Stripe activation pending':'تفعيل Stripe قيد الانتظار','Whish Money':'Whish Money','Apply / Contact CEO':'تقديم طلب / التواصل مع الإدارة',
 'Live financial news board · Market direction and bias · Market structure · Key levels · Strategy and setup context.':'لوحة أخبار مالية مباشرة · اتجاه السوق وانحيازه · هيكل السوق · المستويات الرئيسية · سياق الاستراتيجيات والإعدادات.',
 'Everything in Market Watch · Manual-execution signals · Entry/reference zones · Targets · Stop/invalidation levels · Risk and confidence context.':'كل مزايا مراقبة الأسواق · إشارات للتنفيذ اليدوي · مناطق الدخول والمرجع · الأهداف · مستويات الوقف والإلغاء · سياق المخاطر والثقة.',
 'Everything in Signals · Continuous multi-asset analysis · Opportunity matrix · Risk/position monitoring · Exit and stop alerts · Priority intelligence briefings.':'كل مزايا الإشارات · تحليل مستمر متعدد الأصول · مصفوفة الفرص · مراقبة المخاطر والمراكز · تنبيهات الخروج والوقف · إحاطات استخباراتية ذات أولوية.',
 'Manual application and review · Team access · Custom integrations and deployment planning · Commercial quote based on required services.':'طلب ومراجعة يدوية · وصول للفريق · تكاملات مخصّصة وتخطيط للنشر · عرض تجاري بحسب الخدمات المطلوبة.',
 'Three paid intelligence levels. No free demo and no free trial. Market information is decision-support; broker execution remains under the trader\'s control.':'ثلاثة مستويات مدفوعة للذكاء السوقي. لا توجد نسخة تجريبية مجانية أو فترة تجريبية مجانية. معلومات السوق لدعم القرار، ويبقى تنفيذ أوامر الوسيط تحت تحكم المتداول.',
 'Subscriptions provide market intelligence and monitoring. They do not guarantee outcomes or authorize public subscriber broker execution.':'توفر الاشتراكات ذكاء السوق والمراقبة. لا تضمن النتائج ولا تمنح المشتركين صلاحية تنفيذ أوامر الوسيط عبر المنصة.',
 'Manual payment review':'مراجعة الدفع يدوياً','Email address':'البريد الإلكتروني','Request Whish payment':'طلب الدفع عبر Whish','Back to plans':'العودة إلى الخطط','Reference':'رقم المرجع','Status':'الحالة','Pending review':'بانتظار المراجعة','Monthly price':'السعر الشهري','Recipient':'المستلم','Support':'الدعم','Whish Money is not configured yet.':'الدفع عبر Whish Money غير مُعدّ بعد.','Payment request unavailable.':'طلب الدفع غير متاح.','Payment request storage unavailable.':'تعذّر حفظ طلب الدفع.'
};
const protectedTokens=/\b(?:ATLAS(?:\s+ULTIMATE|\s+Pro)?|JUST AI|MT5|FX|XAUUSD|XAGUSD|EURUSD|GBPUSD|USDJPY|USDCAD|AUDUSD|NZDUSD|BTCUSD|BTCUSDT|ETHUSD|ETHUSDT|SOLUSDT|XRPUSDT|GAS|USD|EUR|GBP|JPY|XAU|XAG)\b/g;
const read=(k,f)=>{try{return localStorage.getItem(k)||f}catch{return f}};const save=(k,v)=>{try{localStorage.setItem(k,v)}catch{}};
let lang=read('atlas-language','en'),theme=read('atlas-theme','dark');if(!['en','ar'].includes(lang))lang='en';if(!['light','dark'].includes(theme))theme='dark';
const reverse=new Map(Object.entries(translations).map(([a,b])=>[b,a]));
const style=document.createElement('style');style.textContent=`.atlas-preferences{display:flex;justify-content:flex-end;gap:12px;flex-wrap:wrap;padding:12px 22px;border-bottom:1px solid #526078;position:relative;z-index:10}.atlas-preferences label{display:flex;align-items:center;gap:6px;font:14px system-ui}.atlas-preferences select{padding:8px;border:1px solid #718096;border-radius:8px;background:#101620;color:#f3f5f7;font:inherit}html{color-scheme:dark}html[data-theme=light]{color-scheme:light}html[data-theme=light] body{--bg:#f7f5ef;--card:#fff;--line:#ccd2dc;--text:#152033;--muted:#475569;--orange:#b54800;--green:#087a43;--red:#b32338;--yellow:#805e00;background:#f7f5ef;color:#152033}html[data-theme=light] .card{background:#fff;color:#152033;border-color:#ccd2dc;box-shadow:0 8px 24px #17233612}html[data-theme=light] .notice{background:#fff2e5;color:#374151}html[data-theme=light] .atlas-preferences select,html[data-theme=light] input{background:#fff;color:#152033}html[dir=rtl] body{font-family:Tahoma,Arial,sans-serif}html[dir=rtl] ul{padding-right:19px;padding-left:0}html[dir=rtl] .notice{border-left:0;border-right:3px solid var(--orange)}html[dir=rtl] input[type=email]{direction:ltr;text-align:left}.atlas-symbol{direction:ltr;unicode-bidi:isolate;display:inline-block}`;document.head.append(style);
const bar=document.createElement('nav');bar.className='atlas-preferences';bar.innerHTML='<label><span id="atlas-lang-label"></span><select id="atlas-lang"><option value="en">English</option><option value="ar">العربية</option></select></label><label><span id="atlas-theme-label"></span><select id="atlas-theme"><option value="dark"></option><option value="light"></option></select></label>';document.body.prepend(bar);
const observer=new MutationObserver(()=>translate());
function translate(){observer.disconnect();document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.dataset.theme=theme;bar.querySelector('#atlas-lang-label').textContent=lang==='ar'?'اللغة':'Language';bar.querySelector('#atlas-theme-label').textContent=lang==='ar'?'المظهر':'Appearance';const mode=bar.querySelector('#atlas-theme');mode.options[0].textContent=lang==='ar'?'داكن':'Dark';mode.options[1].textContent=lang==='ar'?'فاتح':'Light';bar.querySelector('#atlas-lang').value=lang;mode.value=theme;const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(walker.nextNode()){const node=walker.currentNode,parent=node.parentElement;if(!parent||parent.closest('script,style,.atlas-preferences,code,pre'))continue;const text=node.nodeValue.trim();if(!text)continue;const source=reverse.get(text)||text;if(translations[source]){const value=lang==='ar'?translations[source]:source;if(text!==value)node.nodeValue=node.nodeValue.replace(text,value)}}observer.observe(document.body,{subtree:true,childList:true,characterData:true});}
bar.querySelector('#atlas-lang').onchange=e=>{lang=e.target.value;save('atlas-language',lang);translate()};bar.querySelector('#atlas-theme').onchange=e=>{theme=e.target.value;save('atlas-theme',theme);translate()};translate();
})();
"""
