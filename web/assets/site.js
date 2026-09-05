'use strict';
const byId=id=>document.getElementById(id);
function renderDemo() {
  const sample=AtlasDemo.getSample(byId('market').value,byId('scenario').value);
  for(const [id,key] of Object.entries({'market-label':'label','trend-label':'name','structure':'structure','momentum':'momentum','risk':'risk','decision':'decision','explanation':'explanation'})) byId(id).textContent=sample[key];
  byId('quote').textContent=sample.price.toLocaleString('en-US',{minimumFractionDigits:sample.digits,maximumFractionDigits:sample.digits});
  byId('reasons').replaceChildren(...sample.reasons.map(reason=>{const li=document.createElement('li');li.textContent=reason;return li;}));
  const min=Math.min(...sample.values),max=Math.max(...sample.values),range=max-min||1;
  const points=sample.values.map((n,i)=>[(i*624/(sample.values.length-1)+8).toFixed(1),(212-(n-min)/range*182).toFixed(1)]);
  const path=points.map(([x,y],i)=>`${i?'L':'M'}${x} ${y}`).join(' ');
  byId('chart-line').setAttribute('d',path);
  byId('chart-area').setAttribute('d',`${path} L632 235 L8 235 Z`);
  byId('chart-title').textContent=`${sample.market} illustrative price path`;
  byId('chart-desc').textContent=`Synthetic sample values: ${sample.name}. ${sample.explanation} Not live market data.`;
}
byId('market').addEventListener('change',renderDemo);
byId('scenario').addEventListener('change',renderDemo);
byId('reset').addEventListener('click',()=>{byId('market').value='EURUSD';byId('scenario').value='trend';renderDemo();});
byId('share').addEventListener('click',async()=>{
  // Discard existing query parameters so shared links never copy tokens or personal data.
  const url=new URL('/',location.origin);url.hash='demo';
  try{await navigator.clipboard.writeText(url.href);byId('share-status').textContent='Demo link copied.';}
  catch{byId('share-status').textContent=`Copy this demo link: ${url.href}`;}
});
renderDemo();
