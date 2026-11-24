'use strict';
const arabic={
  "Sign up": "إنشاء حساب",
  "YOUR ATLAS ACCOUNT": "حسابك على أطلس",
  "Sign up with Google.": "أنشئ حسابًا باستخدام Google.",
  "Already registered? Use the same button to sign in.": "لديك حساب؟ استخدم الزر نفسه لتسجيل الدخول.",
  "Continue with Google": "المتابعة باستخدام Google",
  "Sign out": "تسجيل الخروج",
  "Create an account or sign in with your Google account.": "أنشئ حسابًا أو سجّل الدخول باستخدام حسابك على Google.",
  "Sign-in does not activate a paid subscription or grant access to a trading account.": "لا يؤدي تسجيل الدخول إلى تفعيل اشتراك مدفوع أو منح صلاحية الوصول إلى حساب تداول.",
  "How your account data is used": "كيف تُستخدم بيانات حسابك",
  "When you continue with Google, Google shares your name and email with ATLAS through Supabase Auth to create and manage your account. Session credentials are stored in this browser to keep you signed in. Signing out clears this browser's session; it does not delete your account. The demo remains free to explore without signing in.": "عند المتابعة باستخدام Google، يشارك Google اسمك وبريدك الإلكتروني مع أطلس عبر Supabase Auth لإنشاء حسابك وإدارته. تُحفظ بيانات الجلسة في هذا المتصفح لإبقائك مسجّل الدخول. يمسح تسجيل الخروج جلسة هذا المتصفح ولا يحذف حسابك. تبقى التجربة متاحة مجانًا دون تسجيل الدخول.",
  "No. Explore all three markets and scenarios freely. Creating an account with Google is optional and does not start a paid subscription.": "لا. استكشف الأسواق الثلاثة وجميع السيناريوهات مجانًا. إنشاء حساب باستخدام Google اختياري ولا يبدأ اشتراكًا مدفوعًا.",
  "Skip to content": "انتقل إلى المحتوى",
  "ATLAS Market home": "الصفحة الرئيسية لأطلس ماركت",
  "MARKET INTELLIGENCE": "رؤى السوق",
  "Main navigation": "التنقل الرئيسي",
  "How it works": "كيف يعمل",
  "Questions": "الأسئلة",
  "Explore demo": "استكشف التجربة",
  "A CLEARER VIEW OF THE MARKET": "رؤية أوضح للسوق",
  "More context.": "فهم أعمق.",
  "Less guesswork.": "تخمين أقل.",
  "Keep control.": "القرار لك.",
  "Bring market structure, momentum, and risk into one view. Explore how ATLAS explains a setup—and when it chooses to wait.": "اجمع بنية السوق والزخم والمخاطر في واجهة واحدة. استكشف كيف يشرح أطلس فرص التداول، ومتى يختار الانتظار.",
  "Try the interactive demo": "جرّب العرض التفاعلي",
  "Meet ATLAS": "تعرّف على أطلس",
  "Free to explore · No account needed · No orders placed": "استكشاف مجاني · دون حساب · دون تنفيذ صفقات",
  "ATLAS principle": "مبدأ أطلس",
  "THE ATLAS APPROACH / 01": "منهج أطلس / 01",
  "A decision is only as useful as the reasoning behind it.": "تأتي قيمة القرار من وضوح الأسباب التي يستند إليها.",
  "Observe.": "راقب.",
  "Understand.": "افهم.",
  "Decide for yourself.": "اتخذ قرارك بنفسك.",
  "EXPLORE THE OBSERVATORY": "استكشف لوحة السوق",
  "One market. The full picture.": "سوق واحد. صورة متكاملة.",
  "Illustrative demo · sample data": "عرض توضيحي · بيانات تجريبية",
  "Choose a market and a scenario. These fixed examples explain the interface; they are not current prices or trading signals.": "اختر سوقًا وسيناريو. تشرح هذه الأمثلة الثابتة الواجهة؛ ولا تمثل أسعارًا حالية أو إشارات تداول.",
  "Market": "السوق",
  "EUR / USD": "اليورو / الدولار",
  "Gold / USD": "الذهب / الدولار",
  "Bitcoin / USD": "بيتكوين / الدولار",
  "Sample scenario": "السيناريو التجريبي",
  "Clear trend": "اتجاه واضح",
  "Mixed signals": "إشارات متعارضة",
  "Event uncertainty": "غموض مرتبط بالأحداث",
  "READ-ONLY EXPLORER": "استكشاف للقراءة فقط",
  "Euro / US Dollar": "اليورو / الدولار الأمريكي",
  "Gold / US Dollar": "الذهب / الدولار الأمريكي",
  "Bitcoin / US Dollar": "بيتكوين / الدولار الأمريكي",
  "24 SAMPLE POINTS": "24 نقطة تجريبية",
  "SAMPLE START": "بداية المثال",
  "ILLUSTRATIVE PATH": "مسار توضيحي",
  "SAMPLE END": "نهاية المثال",
  "Market structure": "بنية السوق",
  "Momentum": "الزخم",
  "Risk context": "سياق المخاطر",
  "SAMPLE DECISION": "قرار توضيحي",
  "WHAT TO NOTICE": "ما الذي يجب ملاحظته",
  "Execution disabled": "تنفيذ الصفقات معطّل",
  "ATLAS / EDUCATIONAL PREVIEW": "أطلس / عرض تعليمي",
  "Reset demo ↺": "إعادة ضبط التجربة ↺",
  "BUILT AROUND UNDERSTANDING": "الفهم هو الأساس",
  "From information to perspective.": "من المعلومات إلى رؤية واضحة.",
  "ATLAS Trading AI organizes the context behind a market decision.": "ينظّم أطلس المعلومات التي تساعد على فهم قرارات السوق.",
  "01 / OBSERVE": "01 / راقب",
  "See the context.": "اطّلع على السياق.",
  "Bring price structure, technical indicators, and broader market information into a common view.": "اجمع بنية الأسعار والمؤشرات الفنية والمعلومات الأوسع عن السوق في عرض موحّد.",
  "02 / UNDERSTAND": "02 / افهم",
  "Read the reasoning.": "افهم الأسباب.",
  "Look at the conditions supporting a setup, the conflicting evidence, and the reasons to wait.": "تعرّف على الظروف الداعمة لفرصة التداول، والأدلة المتعارضة، وأسباب الانتظار.",
  "03 / KEEP CONTROL": "03 / القرار لك",
  "Make your own call.": "اتخذ قرارك بنفسك.",
  "Explore read-only intelligence. The public demo has no broker connection and cannot execute a trade.": "استكشف رؤى السوق للقراءة فقط. هذا العرض غير متصل بوسيط ولا يمكنه تنفيذ أي صفقة.",
  "BEFORE YOU EXPLORE": "قبل أن تبدأ",
  "Clarity starts here.": "الوضوح يبدأ هنا.",
  "A few things to know about this preview.": "معلومات مهمة عن هذا العرض التجريبي.",
  "Is this live market data?": "هل هذه بيانات سوق مباشرة؟",
  "No. The public demo uses fixed, synthetic examples. Every price and scenario is illustrative, with no claim about current market conditions or future performance.": "لا. يستخدم العرض أمثلة ثابتة واصطناعية. جميع الأسعار والسيناريوهات توضيحية، ولا تعكس حالة السوق الحالية أو تتنبأ بالأداء المستقبلي.",
  "Can ATLAS place trades from this website?": "هل يستطيع أطلس تنفيذ صفقات من هذا الموقع؟",
  "No. This public website is read-only and has no access to a brokerage account. The project's MT5 worker runs separately in a private Windows environment.": "لا. هذا الموقع للقراءة فقط ولا يملك صلاحية الوصول إلى حساب وساطة. يعمل مكوّن MT5 الخاص بالمشروع بشكل منفصل في بيئة ويندوز خاصة.",
  "Does the demo require payment or registration?": "هل تتطلب التجربة دفعًا أو تسجيلًا؟",
  "No. Explore all three markets and scenarios freely. This preview does not collect account details or start a subscription.": "لا. يمكنك استكشاف الأسواق الثلاثة وجميع السيناريوهات مجانًا. لا يجمع العرض بيانات الحسابات ولا يبدأ أي اشتراك.",
  "Where is the subscriber dashboard?": "أين لوحة المشتركين؟",
  "The connected dashboard is a separate service that requires a configured data connection and access controls. This public preview does not provide access to private account telemetry.": "لوحة البيانات المتصلة خدمة منفصلة تتطلب إعداد اتصال بالبيانات وضوابط وصول. لا يتيح هذا العرض الاطلاع على بيانات الحسابات الخاصة.",
  "Are these recommendations or return forecasts?": "هل هذه توصيات أو توقعات للعوائد؟",
  "No. ATLAS provides decision-support context. These examples are educational and are not personalized investment advice or a promise of returns.": "لا. يوفّر أطلس معلومات تساعد على فهم القرارات. هذه الأمثلة تعليمية وليست نصائح استثمارية شخصية أو وعودًا بتحقيق عوائد.",
  "START WITH A CLEARER VIEW": "ابدأ برؤية أوضح",
  "Explore the reasoning.": "استكشف الأسباب.",
  "Keep the decision yours.": "واحتفظ بقرارك.",
  "Open the demo": "افتح التجربة",
  "MARKET": "ماركت",
  "Market intelligence. Human judgment.": "رؤى السوق. والقرار للإنسان.",
  "Copy demo link ↗": "انسخ رابط التجربة ↗",
  "Educational sample data only. Trading involves risk, including loss of capital. No personalized investment advice or guaranteed outcomes. This preview uses no analytics cookies or advertising trackers.": "بيانات تجريبية تعليمية فقط. ينطوي التداول على مخاطر، بما فيها خسارة رأس المال. لا تُقدَّم نصائح استثمارية شخصية أو نتائج مضمونة. لا يستخدم هذا العرض ملفات تعريف ارتباط للتحليلات أو أدوات تتبّع إعلانية.",
  "Trend example": "مثال على اتجاه",
  "Observe trend": "راقب الاتجاه",
  "Higher highs": "قمم أعلى",
  "Aligned": "متوافق",
  "Review required": "تستلزم المراجعة",
  "Structure and momentum point in the same direction. This example still needs a defined risk plan before any decision.": "تشير البنية والزخم إلى الاتجاه نفسه. لكن هذا المثال لا يزال يتطلب خطة مخاطر محددة قبل اتخاذ أي قرار.",
  "Price forms higher highs and higher lows.": "يشكّل السعر قممًا وقيعانًا أعلى.",
  "Momentum supports the example trend.": "يدعم الزخم الاتجاه في هذا المثال.",
  "A trend alone does not define acceptable risk.": "الاتجاه وحده لا يحدّد مستوى المخاطرة المقبول.",
  "Mixed example": "مثال على التعارض",
  "Wait for clarity": "انتظر الوضوح",
  "Range-bound": "ضمن نطاق عرضي",
  "Conflicting": "متعارض",
  "No clear setup": "لا توجد فرصة واضحة",
  "Price is moving sideways while momentum changes direction. Conflicting evidence can be a reason to do nothing.": "يتحرك السعر عرضيًا بينما يتغيّر اتجاه الزخم. قد يكون تعارض الأدلة سببًا لعدم اتخاذ أي إجراء.",
  "Price repeatedly returns to the middle of the range.": "يعود السعر مرارًا إلى منتصف النطاق.",
  "Momentum does not confirm a consistent direction.": "لا يؤكّد الزخم اتجاهًا ثابتًا.",
  "Waiting avoids forcing a setup from weak evidence.": "يساعد الانتظار على تجنّب افتعال فرصة استنادًا إلى أدلة ضعيفة.",
  "Event example": "مثال على حدث",
  "Pause and review": "توقّف وراجع",
  "Unstable": "غير مستقر",
  "Unreliable": "غير موثوق",
  "Elevated uncertainty": "غموض مرتفع",
  "An illustrative event shock interrupts the price path. The sample pauses the decision until the uncertainty can be assessed.": "تقطع صدمة افتراضية مرتبطة بحدث مسار السعر. يؤجّل المثال القرار إلى حين تقييم حالة الغموض.",
  "A sudden move disrupts the previous pattern.": "تعطّل حركة مفاجئة النمط السابق.",
  "Recent indicators may no longer describe the conditions.": "قد لا تعود المؤشرات الأخيرة معبّرة عن الظروف الحالية.",
  "Event uncertainty takes priority over a directional view.": "تتقدّم حالة الغموض المرتبطة بالحدث على الرؤية الاتجاهية.",
  "ATLAS Market — Understand the market. Keep control.": "أطلس ماركت — افهم السوق. القرار لك.",
  "Explore ATLAS Trading AI: market context, clear decision explanations, and a free interactive demo. Sample data. No trading account needed.": "استكشف أطلس: سياق السوق، وشروحات واضحة للقرارات، وعرض تفاعلي مجاني ببيانات تجريبية. دون الحاجة إلى حساب تداول.",
  "Try the ATLAS market intelligence demo. Explore market context and see why waiting can be a decision. No account required.": "جرّب عرض أطلس لرؤى السوق. استكشف السياق وافهم لماذا قد يكون الانتظار قرارًا. دون الحاجة إلى حساب."
};
let language='en';
const translate=text=>language==='ar'?(arabic[text]??text):text;
const originalNodes=[];
const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(walker.nextNode()) {
 const node=walker.currentNode;
 if(node.parentElement.closest('script,style,noscript,#language')) continue;
 if(node.textContent.trim()) originalNodes.push([node,node.textContent]);
}
const originalAttributes=[];
for(const element of document.querySelectorAll('[aria-label],meta[name="description"],meta[property="og:title"],meta[property="og:description"]')) {
 if(element.id==='language') continue;
 const attr=element.tagName==='META'?'content':'aria-label';
 originalAttributes.push([element,attr,element.getAttribute(attr)]);
}
const englishTitle=document.title;
function setLanguage(value) {
 language=value==='ar'?'ar':'en';
 document.documentElement.lang=language;
 document.documentElement.dir=language==='ar'?'rtl':'ltr';
 for(const [node,text] of originalNodes) node.textContent=language==='ar'?text.replace(text.trim(),translate(text.trim())):text;
 for(const [element,attr,text] of originalAttributes) element.setAttribute(attr,translate(text));
 document.title=translate(englishTitle);
 const button=document.getElementById('language');
 button.textContent=language==='ar'?'English':'العربية';
 button.lang=language==='ar'?'en':'ar';
 button.setAttribute('aria-label',language==='ar'?'Switch to English':'التبديل إلى العربية');
 document.getElementById('share-status').textContent='';
 try{localStorage.setItem('atlas-language',language);}catch{}
 try{const url=new URL(location.href);url.searchParams.set('lang',language);history.replaceState(null,'',url);}catch{}
 renderDemo();
 document.dispatchEvent(new Event('atlas-language-change'));
}
const byId=id=>document.getElementById(id);
function renderDemo() {
  const sample=AtlasDemo.getSample(byId('market').value,byId('scenario').value);
  for(const [id,key] of Object.entries({'market-label':'label','trend-label':'name','structure':'structure','momentum':'momentum','risk':'risk','decision':'decision','explanation':'explanation'})) byId(id).textContent=translate(sample[key]);
  byId('quote').textContent=sample.price.toLocaleString('en-US',{minimumFractionDigits:sample.digits,maximumFractionDigits:sample.digits});
  byId('reasons').replaceChildren(...sample.reasons.map(reason=>{const li=document.createElement('li');li.textContent=translate(reason);return li;}));
  const min=Math.min(...sample.values),max=Math.max(...sample.values),range=max-min||1;
  const points=sample.values.map((n,i)=>[(i*624/(sample.values.length-1)+8).toFixed(1),(212-(n-min)/range*182).toFixed(1)]);
  const path=points.map(([x,y],i)=>`${i?'L':'M'}${x} ${y}`).join(' ');
  byId('chart-line').setAttribute('d',path);
  byId('chart-area').setAttribute('d',`${path} L632 235 L8 235 Z`);
  byId('chart-title').textContent=language==='ar'?`مسار سعر توضيحي: ${sample.market}`:`${sample.market} illustrative price path`;
  byId('chart-desc').textContent=language==='ar'?`بيانات اصطناعية: ${translate(sample.name)}. ${translate(sample.explanation)} ليست بيانات سوق مباشرة.`:`Synthetic sample values: ${sample.name}. ${sample.explanation} Not live market data.`;
}
byId('market').addEventListener('change',renderDemo);
byId('scenario').addEventListener('change',renderDemo);
byId('reset').addEventListener('click',()=>{byId('market').value='EURUSD';byId('scenario').value='trend';renderDemo();});
byId('share').addEventListener('click',async()=>{
  // Discard existing query parameters so shared links never copy tokens or personal data.
  const url=new URL('/',location.origin);url.searchParams.set('lang',language);url.hash='demo';
  try{await navigator.clipboard.writeText(url.href);byId('share-status').textContent=language==='ar'?'تم نسخ رابط التجربة.':'Demo link copied.';}
  catch{byId('share-status').textContent=(language==='ar'?'انسخ رابط التجربة: ':'Copy this demo link: ')+url.href;}
});
byId('language').addEventListener('click',()=>setLanguage(language==='ar'?'en':'ar'));
let initialLanguage=new URLSearchParams(location.search).get('lang');
if(!['en','ar'].includes(initialLanguage)) {
 try{initialLanguage=localStorage.getItem('atlas-language');}catch{}
}
setLanguage(initialLanguage==='ar'?'ar':'en');
