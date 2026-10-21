const test = require('node:test');
const assert = require('node:assert/strict');
const {safeURL, newsCards, guides, filterCards} = require('../web/assets/atlas-discover.js');

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
