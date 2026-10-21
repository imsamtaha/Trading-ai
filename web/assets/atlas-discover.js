(function (root) {
  'use strict';
  const words = {
    title:['اكتشف. افهم. احتفظ بالفكرة.','Discover. Understand. Keep the idea.'],
    intro:['مساحة واحدة للأخبار وسياق السوق وأدوات التعلّم.','One space for news, market context and learning tools.'],
    all:['الكل','All'],news:['الأخبار','News'],markets:['الأسواق','Markets'],learning:['التعلّم','Learning'],tools:['الأدوات','Tools'],saved:['المحفوظات','Saved'],
    search:['ابحث في البطاقات…','Search the collection…'],clear:['مسح البحث','Clear search'],save:['حفظ','Save'],remove:['إلغاء الحفظ','Unsave'],open:['استكشف','Explore'],
    empty:['لا توجد بطاقات مطابقة. جرّب تصنيفاً آخر أو امسح البحث.','No matching cards. Try another category or clear your search.'],
    loading:['جارٍ جلب الأخبار…','Loading news…'],unavailable:['الأخبار غير متاحة حالياً. بطاقات الشرح والأدوات متاحة أدناه.','News is currently unavailable. Guides and tools are available below.'],
    ready:['الأخبار متاحة • راجع تاريخ كل خبر','News available • Check each publication date'],retry:['تحديث الأخبار','Refresh news'],
    local:['تُحفظ اختياراتك في هذا المتصفح فقط.','Your collection is saved only in this browser.'],failed:['تعذّر حفظ الاختيار في المتصفح؛ سيبقى لهذه الجلسة.','Browser storage is unavailable; saved for this session.'],
    guide:['دليل تعليمي','Learning guide'],context:['سياق السوق','Market context'],workspace:['أداة استكشاف','Workspace tool'],
    original:['العنوان الأصلي • ترجمة عربية غير متاحة','Original headline'],translated:['ترجمة آلية','Machine translation'],arabic:['نص عربي أصلي','Arabic original'],
    unknown:['وقت النشر غير متاح','Publication time unavailable'],count:['بطاقات','cards'],link:['اكتشف','Discover']
  };
  const copy = (key, lang) => words[key][lang === 'ar' ? 0 : 1];
  const sources = new Set(['www.federalreserve.gov','federalreserve.gov','www.ecb.europa.eu','ecb.europa.eu','www.bbc.com','bbc.com','www.bbc.co.uk','bbc.co.uk']);
  function safeURL(value) {
    try { const u = new URL(value); return u.protocol === 'https:' && sources.has(u.hostname) && !u.username && !u.password && (!u.port || u.port === '443') ? u.href : null; } catch { return null; }
  }
  function newsCards(stories, lang) {
    return (Array.isArray(stories) ? stories : []).flatMap(story => {
      if (!story || typeof story !== 'object') return [];
      const url = safeURL(story.url);
      const translated = lang === 'ar' && typeof story.title_ar === 'string' && story.title_ar.trim();
      const title = translated || story.title_en || story.title;
      if (!url || typeof title !== 'string' || !title.trim()) return [];
      const time = new Date(story.published_at || '');
      const stamp = Number.isFinite(time.getTime()) ? time.toLocaleString(lang === 'ar' ? 'ar-LB' : 'en-GB') : copy('unknown',lang);
      const translation = story.translation_status === 'TRANSLATED' && translated ? 'translated' : story.language === 'ar' ? 'arabic' : 'original';
      return [{id:'news:'+url,category:'news',title,body:(story.source_ar && lang === 'ar' ? story.source_ar : story.source) || new URL(url).hostname,meta:stamp+' · '+copy(translation,lang),href:url,external:true,dir:translated || story.language === 'ar' ? 'rtl' : 'ltr',art:'news'}];
    }).slice(0,24);
  }
  function guides(lang, dashboard) {
    const ar = lang === 'ar';
    return [
      {id:'market-context',category:'markets',art:'markets',title:ar?'اقرأ الصورة قبل الحركة.':'Read the context before the move.',body:ar?'اجمع الاتجاه والزخم وحالة البيانات قبل تفسير أي حركة سعر.':'Bring direction, momentum and data freshness into the same view.',href:dashboard?'#hub-markets':'#demo',meta:copy('context',lang)},
      {id:'learning',category:'learning',art:'learning',title:ar?'الانتظار أيضاً قرار.':'Waiting is a decision, too.',body:ar?'تعرّف على تعارض الإشارات وحدود الأمثلة التعليمية قبل اتخاذ قرارك.':'Explore conflicting signals and the limits of illustrative examples.',href:dashboard?'#disclaimer':'#approach',meta:copy('guide',lang)},
      {id:'workspace',category:'tools',art:'tools',title:ar?'من الفكرة إلى مساحة العمل.':'From an idea to your workspace.',body:ar?'افتح لوحة الاستكشاف مع الاحتفاظ بسياق السوق والمخاطر أمامك.':'Open the explorer and keep market context and risk in view.',href:dashboard?'#hub-account':'#demo',meta:copy('workspace',lang)},
      {id:'risk-context',category:'learning',art:'risk',title:ar?'المخاطر جزء من الصورة.':'Risk belongs in the picture.',body:ar?'افصل المعلومات التعليمية عن النتائج الفعلية. راجع المصدر والوقت وحدود البيانات.':'Separate educational context from measured results. Check the source, time and data limitations.',href:dashboard?'#disclaimer':'#questions',meta:copy('guide',lang)}
    ];
  }
  function filterCards(cards, category, query, saved) {
    const term = String(query || '').trim().normalize('NFKC').toLocaleLowerCase();
    return cards.filter(card => (category === 'all' || (category === 'saved' ? saved.has(card.id) : category === card.category)) && (!term || [card.title,card.body,card.meta].join(' ').normalize('NFKC').toLocaleLowerCase().includes(term)));
  }
  const api = {safeURL,newsCards,guides,filterCards};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  const host = document.getElementById('atlas-discover');
  if (!host) return;
  const dashboard = host.dataset.context === 'dashboard';
  let lang = document.documentElement.lang === 'ar' ? 'ar' : 'en';
  let category = 'all', query = '', stories = [], state = 'loading', request = 0;
  let saved = new Set();
  try { const stored = JSON.parse(localStorage.getItem('atlas-discover-saved-v1') || '[]'); if (Array.isArray(stored)) saved = new Set(stored.filter(x => typeof x === 'string').slice(0,500)); } catch {}
  const make = (tag,cls,text) => { const el = document.createElement(tag); if(cls)el.className=cls; if(text!==undefined)el.textContent=text; return el; };
  host.classList.add('atlas-discover');
  const head=make('div','discover-heading'), heading=make('div');
  heading.append(make('p','discover-eyebrow','ATLAS / DISCOVER'));
  const title=make('h2');title.id='discover-title';heading.append(title);
  const intro=make('p','discover-intro');heading.append(intro);
  const number=make('span','discover-number','01 / ∞');number.setAttribute('aria-hidden','true');head.append(heading,number);
  const toolbar=make('div','discover-toolbar'), search=make('input','discover-search');search.type='search';search.maxLength=200;
  const clear=make('button','discover-pill');clear.type='button';
  const filters=make('div','discover-filters');filters.setAttribute('role','group');
  const keys=['all','news','markets','learning','tools','saved'];
  const buttons=keys.map(key=>{const b=make('button','discover-pill');b.type='button';b.dataset.category=key;b.onclick=()=>{category=key;draw();};filters.append(b);return b;});
  toolbar.append(search,clear);
  const statusRow=make('div','discover-status-row'), status=make('p','discover-status');status.setAttribute('role','status');
  const retry=make('button','discover-retry');retry.type='button';retry.onclick=loadNews;statusRow.append(status,retry);
  const count=make('p','discover-count');count.setAttribute('role','status');count.setAttribute('aria-live','polite');
  const grid=make('div','discover-grid'), note=make('p','discover-local');
  host.replaceChildren(head,toolbar,filters,statusRow,count,grid,note);
  host.setAttribute('aria-labelledby','discover-title');
  const navTarget = dashboard ? document.querySelector('.hero .actions') : document.querySelector('header nav');
  const nav=make('a','discover-nav');nav.href='#atlas-discover';if(navTarget)navTarget.append(nav);
  function draw() {
    title.textContent=copy('title',lang);intro.textContent=copy('intro',lang);nav.textContent=copy('link',lang);
    search.placeholder=copy('search',lang);search.setAttribute('aria-label',copy('search',lang));clear.textContent=copy('clear',lang);filters.setAttribute('aria-label',copy('title',lang));
    buttons.forEach((b,i)=>{b.textContent=copy(keys[i],lang);b.setAttribute('aria-pressed',String(category===keys[i]));});
    status.textContent=copy(state,lang);retry.textContent=copy('retry',lang);retry.disabled=state==='loading';
    note.textContent=copy('local',lang);
    const cards=filterCards([...newsCards(stories,lang),...guides(lang,dashboard)],category,query,saved);
    count.textContent=lang==='ar'?'عدد البطاقات: '+cards.length:cards.length+(cards.length===1?' card':' cards');
    grid.replaceChildren();
    for(const card of cards) {
      const article=make('article','discover-card'), art=make('div','discover-art discover-art-'+card.art);art.setAttribute('aria-hidden','true');
      art.append(make('span','discover-art-mark',({markets:'↗',learning:'◎',tools:'⌘',risk:'◈',news:'ATLAS'})[card.art]));
      const content=make('div','discover-card-content'), label=make('span','discover-category',copy(card.category,lang)), h=make('h3','',card.title);if(card.dir)h.dir=card.dir;
      content.append(label,h,make('p','discover-body',card.body),make('p','discover-meta',card.meta));
      const footer=make('div','discover-card-footer'), link=make('a','discover-open',copy('open',lang)+' ↗');link.href=card.href;
      if(card.external){link.target='_blank';link.rel='noopener noreferrer';}
      const save=make('button','discover-save',copy(saved.has(card.id)?'remove':'save',lang));save.type='button';save.setAttribute('aria-pressed',String(saved.has(card.id)));save.setAttribute('aria-label',save.textContent+': '+card.title);
      save.onclick=()=>{const wasSaved=saved.has(card.id);if(wasSaved)saved.delete(card.id);else saved.add(card.id);let failed=false;try{localStorage.setItem('atlas-discover-saved-v1',JSON.stringify([...saved].slice(-500)));}catch{failed=true;}draw();if(failed)note.textContent=copy('failed',lang);const next=[...grid.querySelectorAll('.discover-save')].find(b=>b.dataset.id===card.id);if(next)next.focus();else buttons.find(b=>b.dataset.category===category).focus();};save.dataset.id=card.id;
      footer.append(link,save);content.append(footer);article.append(art,content);grid.append(article);
    }
    if(!cards.length)grid.append(make('p','discover-empty',copy('empty',lang)));
  }
  async function loadNews() {
    const current=++request;const requestLang=lang;state='loading';stories=[];draw();
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
    try {
      const response=await fetch('/dashboard/market-briefing?language='+requestLang,{cache:'no-store',credentials:'same-origin',signal:controller.signal});
      if(!response.ok)throw Error('Unavailable');
      const data=await response.json();if(current!==request)return;
      stories=Array.isArray(data.headlines)?data.headlines:[];state=newsCards(stories,lang).length?'ready':'unavailable';
    } catch {if(current!==request)return;stories=[];state='unavailable';}
    finally {clearTimeout(timer);if(current===request)draw();}
  }
  search.addEventListener('input',()=>{query=search.value;draw();});
  clear.onclick=()=>{query='';search.value='';draw();search.focus();};
  const languageChange=()=>{const next=document.documentElement.lang==='ar'?'ar':'en';if(next!==lang){lang=next;loadNews();}};
  document.addEventListener('atlas-language-change',languageChange);window.addEventListener('atlas-language-change',languageChange);
  new MutationObserver(languageChange).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  window.addEventListener('storage',e=>{if(e.key!=='atlas-discover-saved-v1')return;try{const list=JSON.parse(e.newValue||'[]');if(Array.isArray(list)){saved=new Set(list.filter(x=>typeof x==='string').slice(0,500));draw();}}catch{}});
  loadNews();
})(typeof globalThis !== 'undefined' ? globalThis : this);
