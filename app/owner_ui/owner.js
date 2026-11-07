/* ATLAS Owner: passive, authenticated telemetry viewer. No broker-write paths. */
(() => {
"use strict";
const $ = (id) => document.getElementById(id);
const DATASETS = ["overview","agents","signals","risk","training","decisions","paper_trades","shadow_learning","runtime","mt5_demo"];
const VIEWS = {overview:"overview",council:"agents",signals:"signals",risk:"risk",training:"training",evidence:"decisions",history:"paper_trades",shadow:"shadow_learning",runtime:"runtime",mt5:"mt5_demo"};
const COLUMNS = {
  agents:["name","role","vote","confidence","conflict","weight","sample_count","status","as_of"],
  signals:["symbol","action","confidence","risk","status","source","as_of"],
  decisions:["decision_id","symbol","action","confidence","conflict","risk_verdict","outcome","evidence_id","as_of"],
  paper_trades:["id","decision_id","symbol","direction","status","r_multiple","outcome","opened_at","closed_at"],
  shadow_learning:["agent","decision_id","old_weight","new_weight","sample_count","status","as_of"]
};
const T = {
 ar:{
 workspace:"مساحة الإدارة",overview:"نظرة عامة",council:"مجلس الوكلاء",signals:"الإشارات",risk:"ضوابط المخاطر",training:"التدريب",evidence:"أدلة القرارات",history:"سجل PAPER",shadow:"Shadow Learning",mt5:"حالة MT5 Demo",runtime:"صحة Windows",
 readonly:"مراقبة فقط",sidelock:"لا إرسال أوامر للوسيط",owner:"المالك",private:"OWNER · PRIVATE",historyButton:"السجل",refresh:"تحديث",controlCenter:"ATLAS / مركز التحكم",
 pageTitle:"لوحة التحكم التنفيذية",pageSubtitle:"مراقبة قرارات المجلس والتعلّم الورقي، من دون تنفيذ تداول حقيقي.",lastRefresh:"آخر قراءة",
 safeTitle:"LIVE TRADING DISABLED",safeDesc:"لا يُسمح بأوامر بأموال حقيقية. هذه اللوحة للعرض والتدقيق فقط، وليست منصة لتنفيذ الصفقات.",paperOnly:"PAPER ONLY",
 verification:"إثبات المصدر",dataQuality:"حالة التحقق من البيانات",footer:"بيانات موثّقة المصدر فقط · لا أوامر للوسيط · قراءة فقط",
 paperClosed:"صفقات PAPER المغلقة",decisionsVerified:"القرارات الموثّقة",trainingExamples:"عينات التدريب",agentConfidence:"ثقة المجلس",paperWinRate:"نسبة نجاح PAPER",conflictRate:"تعارض الوكلاء",paperNetR:"نتيجة PAPER (R)",paperOpen:"صفقات PAPER المفتوحة",
 noData:"ما في بيانات متحقق منها لهذا القسم بعد. لازم نوصل تصدير موثّق من Windows/PAPER، وما رح نخترع أرقام للعرض.",
 unverified:"غير موثّق",unavailable:"غير متاح",verified:"تصدير موثّق",sources:"مصادر موثّقة",outOf:"من",search:"بحث في السجلات...",allStatuses:"كل الحالات",rows:"سجل",sort:"ترتيب",
 updated:"آخر تحقق",source:"المصدر",method:"طريقة التحقق",before:"قبل",after:"بعد",delta:"التغيّر",comparison:"مقارنة التدريب قبل وبعد",
 health:"صحة التشغيل",riskNotice:"القيم هنا مؤشرات مراقبة فقط. لا تغيّر إعدادات المخاطر أو تتجاوز صلاحية المخاطر.",
 internal:"خاص بالمالك",noExecution:"بوابة تنفيذ الأوامر",blocked:"معطّلة دائمًا في هذه الواجهة",loadFailed:"فشل تحميل البيانات. تحقق من الاتصال والصلاحيات.",
 liveFlag:"تحذير: رُصد علم ATLAS_LIVE_TRADING=true في الخادم. اللوحة ما زالت قراءة فقط. راجع إعدادات التشغيل فورًا.",
 viewTitle:"عرض البيانات",overviewInfo:"المؤشرات الموثقة من صادرات PAPER والمجلس فقط",count:"العدد",value:"القيمة",notVerified:"لا توجد بيانات أداء موثّقة",
 name:"الوكيل",role:"الدور",vote:"التصويت",confidence:"الثقة",conflict:"التعارض",weight:"الوزن",sample_count:"العينات",status:"الحالة",as_of:"وقت البيانات",
 symbol:"الأصل",action:"القرار",risk:"المخاطر",decision_id:"معرّف القرار",risk_verdict:"قرار المخاطر",outcome:"النتيجة",evidence_id:"الدليل",
 id:"المعرّف",direction:"الاتجاه",r_multiple:"نتيجة R",opened_at:"وقت الفتح",closed_at:"وقت الإغلاق",source:"المصدر",
 agent:"الوكيل",old_weight:"الوزن قبل",new_weight:"الوزن بعد",lesson:"التعلّم",
 risk_per_trade_pct:"المخاطرة لكل صفقة %",daily_loss_limit_pct:"حد الخسارة اليومية %",max_open_risk_pct:"أقصى مخاطرة مفتوحة %",max_positions:"أقصى مراكز",margin_level_floor_pct:"حد الهامش الأدنى %",last_veto:"آخر رفض",veto_count:"مرات رفض المخاطر",gate:"بوابة المخاطر",
 sampleCount:"عدد العينات",accepted:"المقبولة",rejected:"المرفوضة",run_id:"معرّف التدريب",win_rate:"نسبة النجاح",avg_r:"متوسط R",ece:"خطأ المعايرة ECE",brier:"مؤشر Brier",approval_rate:"معدل القبول",
 host:"الجهاز",monitor:"المراقب",heartbeat_at:"آخر نبضة",last_save_at:"آخر حفظ",read_write_check:"اختبار القراءة والكتابة",paper_monitor:"مراقب PAPER",last_error:"آخر خطأ",
 connection:"الاتصال",account_type:"نوع الحساب",broker:"الوسيط",server:"الخادم",last_seen_at:"آخر اتصال",telemetry_status:"حالة البيانات",trade_allowed:"سماح الحساب بالتداول",
 council_confidence:"ثقة المجلس",paper_closed:"صفقات PAPER المغلقة",verified_decisions:"القرارات الموثقة",training_examples:"عينات التدريب",paper_win_rate:"نسبة نجاح PAPER",conflict_rate:"نسبة التعارض",paper_net_r:"نتيجة PAPER (R)",paper_open:"صفقات PAPER المفتوحة",
 training_acceptance:"قبول التدريب",last_cycle_at:"آخر دورة",accepted_count:"العينات المقبولة",rejected_count:"العينات المرفوضة"
 },
 en:{
 workspace:"OWNER WORKSPACE",overview:"Overview",council:"Council agents",signals:"Signals",risk:"Risk controls",training:"Training",evidence:"Decision evidence",history:"PAPER history",shadow:"Shadow Learning",mt5:"MT5 demo status",runtime:"Windows health",
 readonly:"Read only",sidelock:"No broker order submission",owner:"Owner",private:"OWNER · PRIVATE",historyButton:"History",refresh:"Refresh",controlCenter:"ATLAS / CONTROL CENTER",
 pageTitle:"Executive control center",pageSubtitle:"Council decisions and PAPER learning with real-money execution disabled.",lastRefresh:"Last refreshed",
 safeTitle:"LIVE TRADING DISABLED",safeDesc:"No real-money orders are allowed. This is an audit and monitoring dashboard, not an order execution terminal.",paperOnly:"PAPER ONLY",
 verification:"PROVENANCE",dataQuality:"Evidence verification",footer:"Verified-source exports only · No broker orders · Read only",
 paperClosed:"Closed PAPER trades",decisionsVerified:"Verified decisions",trainingExamples:"Training samples",agentConfidence:"Council confidence",paperWinRate:"PAPER win rate",conflictRate:"Agent conflict",paperNetR:"PAPER outcome (R)",paperOpen:"Open PAPER trades",
 noData:"No verified data is available for this section yet. Connect a validated Windows/PAPER export instead of displaying invented figures.",
 unverified:"Unverified",unavailable:"Unavailable",verified:"Verified export",sources:"Verified sources",outOf:"of",search:"Search records...",allStatuses:"All statuses",rows:"rows",sort:"Sort",
 updated:"Verified at",source:"Source",method:"Verification method",before:"Before",after:"After",delta:"Change",comparison:"Training before vs after",
 health:"Runtime health",riskNotice:"These are observational controls, not editable risk settings or permission to bypass risk gates.",
 internal:"Owner only",noExecution:"Broker order gate",blocked:"Always disabled in this dashboard",loadFailed:"Cannot load evidence. Check credentials and connectivity.",
 liveFlag:"Warning: ATLAS_LIVE_TRADING=true was detected on the host. This interface remains read only. Review runtime configuration immediately.",
 viewTitle:"Dataset",overviewInfo:"Verified indicators from PAPER and Council evidence exports only",count:"Count",value:"Value",notVerified:"No verified performance data",
 name:"Agent",role:"Role",vote:"Vote",confidence:"Confidence",conflict:"Conflict",weight:"Weight",sample_count:"Samples",status:"Status",as_of:"As of",
 symbol:"Symbol",action:"Action",risk:"Risk",decision_id:"Decision ID",risk_verdict:"Risk verdict",outcome:"Outcome",evidence_id:"Evidence ID",
 id:"ID",direction:"Direction",r_multiple:"R multiple",opened_at:"Opened",closed_at:"Closed",source:"Source",
 agent:"Agent",old_weight:"Old weight",new_weight:"New weight",lesson:"Lesson",
 risk_per_trade_pct:"Risk per trade %",daily_loss_limit_pct:"Daily loss limit %",max_open_risk_pct:"Max open risk %",max_positions:"Max positions",margin_level_floor_pct:"Min margin level %",last_veto:"Last veto",veto_count:"Risk veto count",gate:"Risk gate",
 sampleCount:"Samples",accepted:"Accepted",rejected:"Rejected",run_id:"Training run",win_rate:"Win rate",avg_r:"Average R",ece:"Calibration error ECE",brier:"Brier score",approval_rate:"Approval rate",
 host:"Host",monitor:"Monitor",heartbeat_at:"Heartbeat",last_save_at:"Last save",read_write_check:"Read/write check",paper_monitor:"PAPER monitor",last_error:"Last error",
 connection:"Connection",account_type:"Account type",broker:"Broker",server:"Server",last_seen_at:"Last seen",telemetry_status:"Telemetry status",trade_allowed:"Broker trading allowed",
 council_confidence:"Council confidence",paper_closed:"Closed PAPER trades",verified_decisions:"Verified decisions",training_examples:"Training samples",paper_win_rate:"PAPER win rate",conflict_rate:"Conflict rate",paper_net_r:"PAPER outcome (R)",paper_open:"Open PAPER trades",
 training_acceptance:"Training acceptance",last_cycle_at:"Last cycle",accepted_count:"Accepted samples",rejected_count:"Rejected samples"
 }
};
const esc = (value) => String(value == null ? "" : value).replace(/[&<>"']/g,(x)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
let lang = "ar", view = "overview", snapshot = null, sortBy = "", sortAsc = true;
try { const chosen = localStorage.getItem("atlas-owner-language"); if (chosen === "en") lang="en"; } catch {}
function tr(key){ return T[lang][key] || key.replace(/_/g," "); }
function formatted(v) {
 if (v === undefined || v === null || v === "") return "—";
 if (typeof v === "boolean") return v ? "✓" : "✕";
 if (typeof v === "number") return Number.isFinite(v) ? v.toLocaleString(lang==="ar"?"ar-LB":"en-US",{maximumFractionDigits:4}) : "—";
 return String(v);
}
function valueHtml(v){return '<span'+(typeof v === "number" ? ' class="numeric"' : "")+'>'+esc(formatted(v))+"</span>";}
function setLanguage() {
 document.documentElement.lang=lang; document.documentElement.dir=lang==="ar"?"rtl":"ltr";
 document.querySelectorAll("[data-i18n]").forEach((element)=>element.textContent=tr(element.dataset.i18n));
 $("languageToggle").textContent=lang==="ar"?"English":"العربية";
 try{localStorage.setItem("atlas-owner-language",lang)}catch{}
 render();
}
function dataset(name){return (snapshot && snapshot.datasets && snapshot.datasets[name]) || (COLUMNS[name]?[]:{});}
function evidence(name){return (snapshot && snapshot.evidence && snapshot.evidence[name]) || {status:"UNAVAILABLE"};}
function verified(name){return evidence(name).status==="VERIFIED_EXPORT";}
function pillText(name){return verified(name)?tr("verified"):evidence(name).status==="UNVERIFIED"?tr("unverified"):tr("unavailable");}
function pillClass(name){return verified(name)?"good":evidence(name).status==="UNVERIFIED"?"warn":"neutral";}
function numbers(){
 const summary=verified("overview")?dataset("overview"):{};
 const metrics=[["paperClosed","paper_closed"],["decisionsVerified","verified_decisions"],["trainingExamples","training_examples"],["agentConfidence","council_confidence"],["paperWinRate","paper_win_rate"],["conflictRate","conflict_rate"],["paperNetR","paper_net_r"],["paperOpen","paper_open"]];
 $("metrics").innerHTML=metrics.map((item)=>'<article class="kpi"><div class="label">'+esc(tr(item[0]))+'</div><div class="number">'+valueHtml(summary[item[1]])+'</div><div class="foot">'+esc(verified("overview")?tr("verified"):tr("notVerified"))+"</div></article>").join("");
}
function quality(){
 const good=DATASETS.filter(verified).length;
 $("sourceSummary").textContent=tr("sources")+": "+good+" "+tr("outOf")+" "+DATASETS.length;
 $("sourceSummary").className="pill "+(good===DATASETS.length?"good":good?"warn":"neutral");
 $("dataQualityList").innerHTML=DATASETS.map((name)=>{const p=evidence(name);return '<div class="quality-item"><b>'+esc(tr(name))+'</b><span class="status '+(verified(name)?"good":"")+'">'+esc(pillText(name))+'</span><small title="'+esc((p.source||""))+'">'+esc(p.source||"—")+'</small></div>';}).join("");
}
function empty(){return '<div class="empty">'+esc(tr("noData"))+"</div>";}
function objectCards(data,exclude){
 const keys=Object.keys(data||{}).filter(k=>!(exclude||[]).includes(k));
 return keys.length?'<div class="mini-card-grid">'+keys.map((k)=>'<div class="mini-card"><span>'+esc(tr(k))+'</span><b>'+valueHtml(data[k])+'</b></div>').join("")+"</div>":empty();
}
function renderOverview(){
 const o=dataset("overview");
 const items=[["training_acceptance",o.training_acceptance],["last_cycle_at",o.last_cycle_at]];
 const html='<div class="mini-card-grid"><div class="mini-card"><span>'+esc(tr("noExecution"))+'</span><b style="color:#65d9aa">'+esc(tr("blocked"))+'</b></div>'+
 items.map((x)=>'<div class="mini-card"><span>'+esc(tr(x[0]))+'</span><b>'+valueHtml(verified("overview")?x[1]:null)+'</b></div>').join("")+"</div>";
 return html + (verified("overview")?'<p class="table-footer">'+esc(tr("overviewInfo"))+"</p>":empty());
}
function renderTable(name) {
 const rows=verified(name)&&Array.isArray(dataset(name))?dataset(name):[];
 if (!rows.length) return empty();
 const cols=COLUMNS[name];
 const statuses=[...new Set(rows.map(x=>String(x.status||x.outcome||x.vote||"")).filter(Boolean))].sort();
 const container=document.createElement("div");
 container.innerHTML='<div class="table-controls"><input type="search" class="input search" id="tableSearch" placeholder="'+esc(tr("search"))+'" aria-label="'+esc(tr("search"))+'"><select id="statusFilter" class="input" aria-label="'+esc(tr("allStatuses"))+'"><option value="">'+esc(tr("allStatuses"))+'</option>'+statuses.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("")+'</select></div><div id="tableResult"></div>';
 $("sectionBody").appendChild(container);
 const search=container.querySelector("#tableSearch"), select=container.querySelector("#statusFilter"), result=container.querySelector("#tableResult");
 function draw(){
  const needle=search.value.trim().toLocaleLowerCase(), status=select.value;
  let filtered=rows.filter(row=>(!status||String(row.status||row.outcome||row.vote||"")===status)&&(!needle||cols.some(k=>String(row[k]??"").toLocaleLowerCase().includes(needle))));
  if(sortBy)filtered=filtered.slice().sort((a,b)=>{const x=a[sortBy],y=b[sortBy];const num=(typeof x==="number"&&typeof y==="number")?x-y:String(x??"").localeCompare(String(y??""),lang==="ar"?"ar":"en",{numeric:true});return sortAsc?num:-num;});
  const visible=filtered.slice(0,250);
  result.innerHTML='<div class="table-wrap"><table><thead><tr>'+cols.map(k=>'<th scope="col"><button type="button" data-sort="'+k+'">'+esc(tr(k))+(sortBy===k?(sortAsc?" ↑":" ↓"):"")+'</button></th>').join("")+'</tr></thead><tbody>'+visible.map(row=>'<tr>'+cols.map(k=>'<td>'+valueHtml(row[k])+'</td>').join("")+'</tr>').join("")+'</tbody></table></div><div class="table-footer">'+visible.length+" / "+filtered.length+" "+esc(tr("rows"))+"</div>";
  result.querySelectorAll("[data-sort]").forEach(button=>button.addEventListener("click",()=>{const k=button.dataset.sort;sortAsc=sortBy===k?!sortAsc:true;sortBy=k;draw();}));
 }
 search.addEventListener("input",draw); select.addEventListener("change",draw); draw();
 return null;
}
function training(){
 const a=dataset("training");
 const left=a.before||{},right=a.after||{};
 const keys=["win_rate","avg_r","ece","brier","conflict_rate","approval_rate","sample_count"].filter(k=>k in left||k in right);
 const comp=keys.length?'<div class="compare">'+keys.map(k=>'<div class="compare-card"><p>'+esc(tr(k))+'</p><div class="values"><span>'+valueHtml(left[k])+'</span><b class="arrow">→</b><span>'+valueHtml(right[k])+'</span></div><p>'+esc(tr("before"))+' / '+esc(tr("after"))+'</p></div>').join("")+"</div>":empty();
 return '<p class="card-kicker">'+esc(tr("comparison"))+"</p>"+comp+objectCards(a,["before","after"]);
}
function renderSection(){
 const name=VIEWS[view];
 $("sectionTitle").textContent=tr(view);
 $("sectionKicker").textContent=view==="overview"?"ATLAS CONTROL":"ATLAS EVIDENCE / "+name.toUpperCase();
 $("sectionStatus").textContent=view==="overview"?pillText("overview"):pillText(name);
 $("sectionStatus").className="pill "+pillClass(name);
 $("sectionBody").innerHTML="";
 if(view==="overview"){$("sectionBody").innerHTML=renderOverview();return;}
 if(!verified(name)){$("sectionBody").innerHTML=empty();return;}
 if(COLUMNS[name]){renderTable(name);return;}
 if(view==="training"){$("sectionBody").innerHTML=training();return;}
 if(view==="risk"){
  $("sectionBody").innerHTML='<p class="table-footer">'+esc(tr("riskNotice"))+"</p>"+objectCards(dataset(name));
  return;
 }
 $("sectionBody").innerHTML=objectCards(dataset(name));
}
function render(){
 document.querySelectorAll("[data-view]").forEach(b=>{b.classList.toggle("active",b.dataset.view===view);b.setAttribute("aria-current",b.dataset.view===view?"page":"false");});
 if(!snapshot)return;
 $("fetchedAt").textContent=new Date(snapshot.fetched_at).toLocaleString(lang==="ar"?"ar-LB":"en-US");
 $("runtimeAlert").hidden=!snapshot.runtime_live_flag_enabled;
 $("runtimeAlert").textContent=snapshot.runtime_live_flag_enabled?tr("liveFlag"):"";
 numbers();quality();renderSection();
}
async function refresh(){
 $("refreshAction").disabled=true;
 try{
  const response=await fetch("/sam/api/snapshot",{credentials:"same-origin",cache:"no-store",headers:{"Accept":"application/json"}});
  if(!response.ok)throw Error("HTTP "+response.status);
  const data=await response.json();
  if(data.mode!=="PAPER_READ_ONLY"||data.broker_execution_allowed!==false||data.live_orders_allowed!==false)throw Error("Unexpected dashboard mode");
  snapshot=data;render();
 }catch(err){
  $("runtimeAlert").hidden=false;
  $("runtimeAlert").textContent=tr("loadFailed")+" ("+String(err.message||"error")+")";
 }finally{$("refreshAction").disabled=false;}
}
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{
 view=b.dataset.view;sortBy="";sortAsc=true;render();if(window.innerWidth<900)$("sectionBody").scrollIntoView({block:"nearest",behavior:"smooth"});
}));
$("refreshAction").addEventListener("click",refresh);
$("historyAction").addEventListener("click",()=>{view="history";sortBy="";render();$("sectionBody").scrollIntoView({behavior:"smooth",block:"nearest"});});
$("languageToggle").addEventListener("click",()=>{lang=lang==="ar"?"en":"ar";setLanguage();});
setLanguage();refresh();
})();