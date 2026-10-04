(function (root) {
  'use strict';
  const hosts = new Set(['www.federalreserve.gov','federalreserve.gov','www.ecb.europa.eu','ecb.europa.eu','www.bbc.com','bbc.com','www.bbc.co.uk','bbc.co.uk']);
  const categories = {MACRO:['الاقتصاد الكلي','Macro'],FX:['العملات','FX'],COMMODITIES:['السلع','Commodities'],DIGITAL_ASSETS:['الأصول الرقمية','Digital assets'],EQUITIES:['الأسهم','Equities'],GENERAL:['أخبار عامة','General news']};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function safeLink(value) {
    try { const u = new URL(value); return u.protocol === 'https:' && hosts.has(u.hostname) && !u.username && !u.password && (!u.port || u.port === '443'); }
    catch { return false; }
  }
  function render(target, stories, language = 'ar') {
    const arabic = language === 'ar';
    const rows = (Array.isArray(stories) ? stories : []).filter(x => x && safeLink(x.url)).slice(0,3);
    target.innerHTML = rows.map(x => {
      const translated = arabic && x.title_ar;
      const title = translated || x.title_en || x.title;
      const note = arabic ? ({TRANSLATED:'ترجمة آلية', ORIGINAL_ARABIC:'نص عربي أصلي'}[x.translation_status] || 'الترجمة العربية غير متاحة') : (x.language === 'ar' ? 'Arabic original' : 'Original headline');
      const age = x.freshness === 'FRESH' ? (arabic ? 'حديث' : 'Recent') : (arabic ? 'قديم' : 'Old');
      const category = x.routing && Object.hasOwn(categories,x.routing.category) ? categories[x.routing.category][arabic ? 0 : 1] : null;
      const routing = category ? ' · '+esc(category) : '';
      const dir = translated || x.language === 'ar' ? 'rtl' : 'ltr';
      const date = new Date(x.published_at);
      const stamp = Number.isFinite(date.getTime()) ? date.toLocaleString(arabic ? 'ar-LB' : 'en-GB') : (arabic ? 'وقت غير متاح' : 'Time unavailable');
      return '<a class="story" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer"><b dir="'+dir+'">'+esc(title)+'</b><div class="mini">'+esc(arabic ? (x.source_ar || x.source) : x.source)+' · '+esc(stamp)+' · '+age+' · '+note+routing+'</div></a>';
    }).join('') || '<div class="empty">'+(arabic ? 'الأخبار غير متاحة حالياً.' : 'News temporarily unavailable.')+'</div>';
  }
  const api = {render};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AtlasNews = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
