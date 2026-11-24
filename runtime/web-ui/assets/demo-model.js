/* Fixed, synthetic teaching examples. No market-data or brokerage requests. */
(function (root) {
  'use strict';
  const markets = {
    EURUSD: {label: 'Euro / US Dollar', base: 1.0842, scale: 0.00013, digits: 4},
    XAUUSD: {label: 'Gold / US Dollar', base: 2348.50, scale: 1.7, digits: 2},
    BTCUSD: {label: 'Bitcoin / US Dollar', base: 64280, scale: 55, digits: 0}
  };
  const scenarios = {
    trend: {name:'Trend example', decision:'Observe trend', structure:'Higher highs', momentum:'Aligned', risk:'Review required',
      explanation:'Structure and momentum point in the same direction. This example still needs a defined risk plan before any decision.',
      reasons:['Price forms higher highs and higher lows.','Momentum supports the example trend.','A trend alone does not define acceptable risk.'],
      path:[2,3,2,4,6,5,6,9,8,10,9,12,11,10,13,15,14,17,16,18,17,20,19,21]},
    mixed: {name:'Mixed example', decision:'Wait for clarity', structure:'Range-bound', momentum:'Conflicting', risk:'No clear setup',
      explanation:'Price is moving sideways while momentum changes direction. Conflicting evidence can be a reason to do nothing.',
      reasons:['Price repeatedly returns to the middle of the range.','Momentum does not confirm a consistent direction.','Waiting avoids forcing a setup from weak evidence.'],
      path:[10,13,16,12,8,6,10,14,15,11,7,8,12,16,14,10,6,9,12,14,11,8,10,11]},
    event: {name:'Event example', decision:'Pause and review', structure:'Unstable', momentum:'Unreliable', risk:'Elevated uncertainty',
      explanation:'An illustrative event shock interrupts the price path. The sample pauses the decision until the uncertainty can be assessed.',
      reasons:['A sudden move disrupts the previous pattern.','Recent indicators may no longer describe the conditions.','Event uncertainty takes priority over a directional view.'],
      path:[5,7,6,8,7,9,8,10,9,11,10,12,11,28,7,23,3,18,5,16,7,14,9,12]}
  };
  function getSample(market, scenario) {
    if (!Object.hasOwn(markets, market) || !Object.hasOwn(scenarios, scenario)) throw new Error('Unknown demo selection');
    const m=markets[market], s=scenarios[scenario];
    const values=s.path.map(n=>Number((m.base+(n-s.path[s.path.length-1])*m.scale).toFixed(m.digits+1)));
    return {...s, market, label:m.label, digits:m.digits, price:m.base, values, reasons:[...s.reasons], mode:'synthetic_demo', live:false, execution_enabled:false};
  }
  const model={getSample};
  if(typeof module!=='undefined' && module.exports) module.exports=model;
  else root.AtlasDemo=model;
})(typeof globalThis!=='undefined'?globalThis:this);
