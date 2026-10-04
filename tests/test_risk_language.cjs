const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const script=execFileSync(process.env.PYTHON || 'python',['-c','from app.dashboard.preferences import SCRIPT; print(SCRIPT)'],{encoding:'utf8'});

test('risk words switch both ways and refreshed risk states use selected language',()=>{
 const nodes=['Risk','LOW','MEDIUM','HIGH','EXTREME','PASSED','REJECTED','Risk: BLOCKED'].map(text=>({nodeValue:text,parentElement:{closest:()=>null}}));
 const controls={};
 for(const id of ['atlas-lang-label','atlas-theme-label','atlas-lang','atlas-theme'])controls['#'+id]={options:[{},{}]};
 const bar={querySelector:id=>controls[id]};
 let callback;
 const body={prepend:()=>{}};
 const context={localStorage:{getItem:key=>key==='atlas-language'?'ar':null,setItem:()=>{}},NodeFilter:{SHOW_TEXT:4},
  MutationObserver:class{constructor(fn){callback=fn}disconnect(){}observe(){}},
  CustomEvent:class{},window:{dispatchEvent:()=>{}},
  document:{documentElement:{lang:'ar',dataset:{}},body,head:{append:()=>{}},
   createElement:name=>name==='nav'?bar:{},createTreeWalker:()=>{let i=-1;return{nextNode(){return ++i<nodes.length},get currentNode(){return nodes[i]}}}}};
 vm.runInNewContext(script,context);
 assert.deepEqual(nodes.map(x=>x.nodeValue),['المخاطر','منخفض','متوسط','مرتفع','شديد جداً','مقبول','مرفوض','المخاطر: محظور']);
 controls['#atlas-lang'].onchange({target:{value:'en'}});
 assert.deepEqual(nodes.map(x=>x.nodeValue),['Risk','LOW','MEDIUM','HIGH','EXTREME','PASSED','REJECTED','Risk: BLOCKED']);
 controls['#atlas-lang'].onchange({target:{value:'ar'}});
 nodes[1].nodeValue='LOW';callback();
 assert.equal(nodes[1].nodeValue,'منخفض');
});
