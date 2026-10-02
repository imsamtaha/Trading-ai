const test = require('node:test');
const assert = require('node:assert/strict');
const news = require('../web/assets/atlas-news.js');
const story = {title:'Rates unchanged',title_en:'Rates unchanged',title_ar:'الفائدة دون تغيير',
 url:'https://www.ecb.europa.eu/press/story',source:'ECB',source_ar:'البنك المركزي الأوروبي',
 published_at:'2026-10-02T13:00:00+00:00',translation_status:'TRANSLATED',freshness:'FRESH'};

test('news replaces previous content with at most three rows',()=>{
 const target = {innerHTML:'old headlines'};
 news.render(target,Array(8).fill(story),'ar');
 assert.equal((target.innerHTML.match(/class="story"/g)||[]).length,3);
 assert.ok(!target.innerHTML.includes('old headlines'));
 assert.ok(target.innerHTML.includes('الفائدة دون تغيير'));
 assert.ok(target.innerHTML.includes('ترجمة آلية'));
 news.render(target,[],'ar');
 assert.ok(!target.innerHTML.includes('class="story"'));
 assert.ok(target.innerHTML.includes('غير متاحة'));
});

test('language switching shows original English and marks unavailable Arabic',()=>{
 const target={};
 news.render(target,[story],'en');
 assert.ok(target.innerHTML.includes('Rates unchanged'));
 assert.ok(!target.innerHTML.includes('الفائدة دون تغيير'));
 news.render(target,[{...story,title_ar:null,translation_status:'UNAVAILABLE'}],'ar');
 assert.ok(target.innerHTML.includes('Rates unchanged'));
 assert.ok(target.innerHTML.includes('الترجمة العربية غير متاحة'));
});

test('news escapes publisher content and drops unsafe URLs',()=>{
 const target={};
 news.render(target,[{...story,title_ar:'<script>alert(1)</script>'},{...story,url:'javascript:alert(1)'},{...story,url:'https://www.ecb.europa.eu.evil.example/a'}],'ar');
 assert.ok(target.innerHTML.includes('&lt;script&gt;'));
 assert.ok(!target.innerHTML.includes('<script>'));
 assert.equal((target.innerHTML.match(/class="story"/g)||[]).length,1);
});

test('native Arabic stays original and old publication is clearly marked',()=>{
 const target={};
 news.render(target,[{...story,translation_status:'ORIGINAL_ARABIC',freshness:'STALE'}],'ar');
 assert.ok(target.innerHTML.includes('نص عربي أصلي'));
 assert.ok(target.innerHTML.includes('قديم'));
 assert.ok(!target.innerHTML.includes('ترجمة آلية'));
});
