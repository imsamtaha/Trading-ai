const test = require('node:test');
const assert = require('node:assert/strict');
const {safeURL, newsCards, guides, filterCards, validSavedNews, combineNewsCards} = require('../web/assets/atlas-discover.js');

test('news URLs reject executable, credential-bearing and lookalike destinations', () => {
  for (const url of ['javascript:alert(1)','http://bbc.com/news','https://bbc.com.evil.test/a','https://user:pass@bbc.com/news','https://bbc.com:444/a','/private']) assert.equal(safeURL(url),null);
  assert.equal(safeURL('https://www.bbc.com/news/example'),'https://www.bbc.com/news/example');
});
test('malformed news yields no invented headlines', () => {
  assert.deepEqual(newsCards(null,'ar'),[]);
  assert.deepEqual(newsCards([null,{}, {url:'https://bbc.com/a',title:42}, {url:'https://evil.test',title:'bad'}],'ar'),[]);
});
test('Arabic news labels missing translations and invalid times honestly', () => {
  const [card] = newsCards([{url:'https://bbc.com/a',title:'Original',published_at:'bad'}],'ar');
  assert.equal(card.title,'Original'); assert.equal(card.dir,'ltr');
  assert.match(card.meta,/ترجمة عربية غير متاحة/); assert.match(card.meta,/وقت النشر غير متاح/);
  const [translated]=newsCards([{url:'https://bbc.com/a',title:'Original',title_ar:'عنوان عربي',translation_status:'TRANSLATED'}],'ar');
  assert.equal(translated.dir,'rtl'); assert.match(translated.meta,/ترجمة آلية/);
});
test('filters combine category, normalized query and saved selection', () => {
  const cards=guides('en',false), saved=new Set(['risk-context']);
  assert.equal(filterCards(cards,'learning','',saved).length,2);
  assert.equal(filterCards(cards,'saved','risk',saved)[0].id,'risk-context');
  assert.equal(filterCards(cards,'markets','risk',saved).length,0);
  assert.equal(filterCards(cards,'all','ＷＡＩＴＩＮＧ',saved).length,1);
  assert.equal(filterCards(guides('ar',true),'all','المخاطر',saved).length,2);
});
test('guide destinations remain in the existing website or dashboard', () => {
  for(const dashboard of [false,true]) for(const lang of ['ar','en']) {
    const cards=guides(lang,dashboard);assert.equal(new Set(cards.map(c=>c.id)).size,cards.length);
    for(const card of cards) assert.match(card.href,/^#[a-z-]+$/);
    assert.equal(cards[0].href,dashboard?'#hub-markets':'#demo');
  }
});

test('bookmarked cards survive a failed briefing and discard unsafe stored values', () => {
  const url='https://www.bbc.com/news/saved-example';
  const card=newsCards([{url,title:'Archive article',published_at:'2026-10-01T12:00:00Z'}],'en')[0];
  const stored=JSON.parse(JSON.stringify([card]));
  const recovered=validSavedNews([...stored,{...card,id:'news:https://evil.test',href:'https://evil.test/a'},{...card,id:'wrong'},null]);
  assert.equal(recovered.length,1);
  assert.equal(recovered[0].href,url);
  assert.equal(recovered[0].category,'news');
  assert.equal(combineNewsCards([],recovered,new Set([card.id])).length,1);
  assert.equal(filterCards(combineNewsCards([],recovered,new Set([card.id])),'saved','archive',new Set([card.id])).length,1);
  assert.equal(combineNewsCards([],recovered,new Set()).length,0);
});
test('live articles replace cached duplicates with refreshed source metadata', () => {
  const url='https://bbc.com/news/item';
  const cached=newsCards([{url,title:'Old title'}],'en');
  const fresh=newsCards([{url,title:'Current title'}],'en');
  const cards=combineNewsCards(fresh,cached,new Set([fresh[0].id]));
  assert.equal(cards.length,1);
  assert.equal(cards[0].title,'Current title');
});
test('dashboard shares the market-briefing request and Discover defaults to dark colors',()=>{
  const fs=require('node:fs');
  const view=fs.readFileSync(require('node:path').join(__dirname,'../app/dashboard/views.py'),'utf8');
  const css=fs.readFileSync(require('node:path').join(__dirname,'../web/assets/atlas-discover.css'),'utf8');
  const discover=fs.readFileSync(require('node:path').join(__dirname,'../web/assets/atlas-discover.js'),'utf8');
  assert.match(view,/window\.atlasGetMarketBriefing=atlasGetMarketBriefing/);
  assert.match(view,/let d=await atlasGetMarketBriefing\(language\)/);
  assert.match(discover,/data=await window\.atlasGetMarketBriefing\(requestLang\)/);
  assert.match(css,/\.atlas-discover\{--dc-bg:#111925;/);
  assert.match(css,/html\[data-theme=light\] \.atlas-discover/);
});
