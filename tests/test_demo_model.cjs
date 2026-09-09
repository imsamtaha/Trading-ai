const test = require('node:test');
const assert = require('node:assert/strict');
const {getSample} = require('../web/assets/demo-model.js');

test('all nine selections yield finite chart data and clearly simulated states',()=>{
  for(const market of ['EURUSD','XAUUSD','BTCUSD']) {
    for(const scenario of ['trend','mixed','event']) {
      const s=getSample(market,scenario);
      assert.equal(s.values.length,24);
      assert(s.values.every(Number.isFinite));
      assert.equal(s.values.at(-1),s.price);
      assert.equal(s.mode,'synthetic_demo');
      assert.equal(s.live,false);
      assert.equal(s.execution_enabled,false);
      assert(s.reasons.length>0);
    }
  }
});
test('conflicting and event scenarios do not imply an executable setup',()=>{
  assert.equal(getSample('EURUSD','mixed').decision,'Wait for clarity');
  assert.equal(getSample('EURUSD','event').decision,'Pause and review');
});
test('unknown and inherited selections are rejected',()=>{
  assert.throws(()=>getSample('EURUSD','unknown'));
  assert.throws(()=>getSample('__proto__','trend'));
  assert.throws(()=>getSample('EURUSD','constructor'));
});
