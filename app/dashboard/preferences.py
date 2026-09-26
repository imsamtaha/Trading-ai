from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/ui/preferences.js", include_in_schema=False)
def preferences_script():
    return Response(SCRIPT, media_type="application/javascript")


SCRIPT = r"""
(()=>{
const translations={
 'ATLAS THE ULTIMATE':'أطلس',
 'Read the market. Keep control.':'اقرأ السوق. وابقَ متحكّماً.',
 'Reader plans provide observational access to ATLAS telemetry and market context. They do not provide account control, personal investment advice, or any promise of returns.':'تتيح خطط القرّاء متابعة بيانات أطلس وسياق السوق فقط. لا تمنح التحكم بالحساب أو استشارات استثمارية شخصية أو وعوداً بالعوائد.',
 'ATLAS READER':'أطلس للقارئ','ATLAS PRO READER':'أطلس للقارئ المتقدّم',
 '/month':'/شهرياً','3-day free trial':'تجربة مجانية لمدة 3 أيام',
 'Live read-only MT5 telemetry':'متابعة بيانات MT5 للقراءة فقط',
 'Wall Street and financial-news board':'لوحة وول ستريت والأخبار المالية',
 'Open positions and floating P/L':'الصفقات المفتوحة والربح والخسارة غير المحقّقين',
 'Everything in Reader':'كل مزايا خطة القارئ',
 'Expanded multi-asset opportunity matrix':'متابعة موسّعة لفرص الأسواق المتعددة',
 'Priority subscriber briefings':'إحاطات المشتركين ذات الأولوية',
 'Start free trial':'ابدأ التجربة المجانية','Pay with Whish Money':'الدفع عبر Whish Money',
 'Whish requests are reviewed manually. Automatic renewal is not available.':'تُراجع طلبات Whish يدوياً. التجديد التلقائي غير متاح.',
 'Subscriber Observatory · Read-only live telemetry':'لوحة المشتركين · بيانات مباشرة للقراءة فقط',
 'Reader plans':'خطط القرّاء','CONNECTING':'جارٍ الاتصال','OFFLINE':'غير متصل','ONLINE':'متصل',
 'VERIFIED LIVE':'حساب حقيقي تم التحقّق منه','Account Type':'نوع الحساب',
 'Equity':'حقوق الحساب','Balance':'الرصيد','Floating P/L':'الربح والخسارة غير المحقّقين',
 'Open Positions':'الصفقات المفتوحة','Execution Gate':'حالة التنفيذ',
 'ATLAS Opportunity Matrix':'فرص الأسواق في أطلس','Verified Account':'الحساب المتحقّق منه',
 'Subscriptions':'الاشتراكات','Continue with Google':'المتابعة باستخدام Google','Email code':'رمز البريد الإلكتروني','Private ATLAS Dashboard':'لوحة أطلس الخاصة','Live Asset Viewer':'مراقبة الأصل مباشرة','Asset':'الأصل',
 'Live Demo Trading':'التداول التجريبي المباشر','Current Price':'السعر الحالي',
 'Buy Demo':'شراء تجريبي','Sell Demo':'بيع تجريبي','Close Demo Position':'إغلاق الصفقة التجريبية',
 'No demo position open.':'لا توجد صفقة تجريبية مفتوحة.','Entry':'سعر الدخول','Demo P/L':'الربح والخسارة التجريبية',
 'Live prices update from the connected FxPro MT5 demo feed.':'تتحدّث الأسعار مباشرة من حساب FxPro MT5 التجريبي المتصل.',
 'Demo only. These controls never submit an order to MT5 or FxPro.':'وضع تجريبي فقط. هذه الأزرار لا ترسل أي أمر إلى MT5 أو FxPro.',
 'Live demo telemetry · Demo market viewer · No broker order submission':'بيانات تجريبية مباشرة · مراقبة السوق · من دون إرسال أوامر للوسيط',
 'score':'النتيجة','confidence':'الثقة','opportunity':'الفرصة',
 'AI Chart':'الرسم البياني بالذكاء الاصطناعي','AI Trend':'اتجاه الذكاء الاصطناعي','AI Momentum':'زخم الذكاء الاصطناعي',
 'AI Signal':'إشارة الذكاء الاصطناعي','AI Confidence':'ثقة الذكاء الاصطناعي','Timeframe':'الإطار الزمني','OBSERVE':'مراقبة',
 'FOREX':'فوركس','METALS':'معادن','INDICES':'مؤشرات','ENERGY':'طاقة',
 'ATLAS VERIFIED ACCOUNT':'حساب أطلس المتحقق منه',
 'Wall Street Board · Context only':'لوحة وول ستريت · للسياق فقط',
 'Financial News · Context only':'الأخبار المالية · للسياق فقط',
 'Read-only telemetry. Trading involves risk.':'بيانات للقراءة فقط. التداول ينطوي على مخاطر.',
 'Live demo telemetry and execution status. Real-money execution requires an approved REAL account, explicit owner acknowledgement, and broker trade permission. Past or current results do not guarantee future performance.':'بيانات تجريبية مباشرة وحالة التنفيذ. التداول بأموال حقيقية يتطلب حساباً حقيقياً معتمداً وموافقة صريحة وصلاحية تداول من الوسيط. النتائج السابقة أو الحالية لا تضمن الأداء المستقبلي.',
 'Read-only account and strategy telemetry. Past or current results do not guarantee future performance.':'بيانات الحساب والاستراتيجية للقراءة فقط. النتائج السابقة أو الحالية لا تضمن الأداء المستقبلي.',
 'No markets available.':'لا توجد أسواق متاحة.','No open positions.':'لا توجد صفقات مفتوحة.',
 'Market data temporarily unavailable.':'بيانات السوق غير متاحة مؤقتاً.',
 'Financial headlines temporarily unavailable.':'الأخبار المالية غير متاحة مؤقتاً.',
 'Market board unavailable.':'لوحة السوق غير متاحة.','Headlines unavailable.':'الأخبار غير متاحة.',
 'PRIVATE':'خاص','DEMO':'تجريبي','REAL':'حقيقي','UNKNOWN':'غير معروف',
 'ENABLED':'مفعّل','DISABLED':'معطّل','WAIT':'انتظار','BUY':'شراء','SELL':'بيع','LONG':'شراء','SHORT':'بيع','OPEN':'مفتوح','CLOSED':'مغلق',
 'BULLISH':'صاعد','BEARISH':'هابط','NEUTRAL':'محايد','NO_TRADE':'لا صفقة',
 'Manual payment review':'مراجعة الدفع يدوياً',
 'Request your 3-day trial first. Contact support to confirm the start date and payment instructions. Monthly renewals are manual.':'اطلب تجربتك لمدة 3 أيام أولاً. تواصل مع الدعم لتأكيد تاريخ البدء وتعليمات الدفع. التجديد الشهري يدوي.',
 'A request or receipt does not activate access. Payment must be verified by the owner.':'الطلب أو الإيصال لا يفعّل الوصول. يجب أن يتحقّق صاحب المنصة من الدفع.',
 'Email address':'البريد الإلكتروني','Request Whish payment':'طلب الدفع عبر Whish',
 'Back to plans':'العودة إلى الخطط','Reference':'رقم المرجع','Status':'الحالة',
 'Pending review':'بانتظار المراجعة','Monthly price':'السعر الشهري',
 'Recipient':'المستلم','Support':'الدعم',
 'Whish Money is not configured yet.':'الدفع عبر Whish Money غير مُعدّ بعد.',
 'Payment request unavailable.':'طلب الدفع غير متاح.',
 'Payment request storage unavailable.':'تعذّر حفظ طلب الدفع.',
};
const read=(k,f)=>{try{return localStorage.getItem(k)||f}catch{return f}};
const save=(k,v)=>{try{localStorage.setItem(k,v)}catch{}};
let lang=read('atlas-language','en'),theme=read('atlas-theme','dark');
if(!['en','ar'].includes(lang))lang='en';
if(!['light','dark'].includes(theme))theme='dark';
const reverse=new Map(Object.entries(translations).map(([a,b])=>[b,a]));
const style=document.createElement('style');
style.textContent=`
.atlas-preferences{display:flex;justify-content:flex-end;gap:12px;flex-wrap:wrap;padding:12px 22px;border-bottom:1px solid #526078;position:relative;z-index:10}
.atlas-preferences label{display:flex;align-items:center;gap:6px;font:14px system-ui}
.atlas-preferences select{padding:8px;border:1px solid #718096;border-radius:8px;background:#101620;color:#f3f5f7;font:inherit}
html{color-scheme:dark}html[data-theme=light]{color-scheme:light}
html[data-theme=light] body{--bg:#f7f5ef;--card:#fff;--line:#ccd2dc;--text:#152033;--muted:#475569;--orange:#b54800;--green:#087a43;--red:#b32338;--yellow:#805e00;background:#f7f5ef;color:#152033}
html[data-theme=light] .card{background:#fff;color:#152033;border-color:#ccd2dc;box-shadow:0 8px 24px #17233612}
html[data-theme=light] .notice{background:#fff2e5;color:#374151}
html[data-theme=light] .atlas-preferences select,html[data-theme=light] input{background:#fff;color:#152033}
html[data-theme=light] p,html[data-theme=light] ul{color:#475569}
html[data-theme=light] a{color:#994000}
html[data-theme=light] button{background:#ff8a24;color:#111}
html[dir=rtl] body{font-family:Tahoma,Arial,sans-serif}
html[dir=rtl] ul{padding-right:19px;padding-left:0}
html[dir=rtl] .notice{border-left:0;border-right:3px solid var(--orange)}
html[dir=rtl] input[type=email]{direction:ltr;text-align:left}
`;document.head.append(style);
const bar=document.createElement('nav');bar.className='atlas-preferences';
bar.innerHTML='<label><span id="atlas-lang-label"></span><select id="atlas-lang"><option value="en">English</option><option value="ar">العربية</option></select></label><label><span id="atlas-theme-label"></span><select id="atlas-theme"><option value="dark"></option><option value="light"></option></select></label>';
document.body.prepend(bar);
const observer=new MutationObserver(()=>translate());
function translate(){
 observer.disconnect();
 document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.dataset.theme=theme;
 bar.querySelector('#atlas-lang-label').textContent=lang==='ar'?'اللغة':'Language';
 bar.querySelector('#atlas-theme-label').textContent=lang==='ar'?'المظهر':'Appearance';
 const mode=bar.querySelector('#atlas-theme');mode.options[0].textContent=lang==='ar'?'داكن':'Dark';mode.options[1].textContent=lang==='ar'?'فاتح':'Light';
 bar.querySelector('#atlas-lang').value=lang;mode.value=theme;
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()){
  const node=walker.currentNode,parent=node.parentElement;
  if(!parent||parent.closest('script,style,.atlas-preferences,code,pre'))continue;
  const text=node.nodeValue.trim();if(!text)continue;
  const source=reverse.get(text)||text;
  if(translations[source]){const value=lang==='ar'?translations[source]:source;
   if(text!==value)node.nodeValue=node.nodeValue.replace(text,value)}
 }
 observer.observe(document.body,{subtree:true,childList:true,characterData:true});
}
bar.querySelector('#atlas-lang').onchange=e=>{lang=e.target.value;save('atlas-language',lang);translate()};
bar.querySelector('#atlas-theme').onchange=e=>{theme=e.target.value;save('atlas-theme',theme);translate()};
translate();
})();
"""
