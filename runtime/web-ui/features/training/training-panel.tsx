"use client";
import {useEffect,useState} from "react";
import {atlasFetch} from "@/lib/api/client";
import {apiPath} from "@/lib/api/config";
import {PaperEvidence, type PaperTrade, type TrainingSession, type ShadowReview} from "./paper-evidence";
import styles from "./training-panel.module.css";
type Overview={paper_trades?:PaperTrade[];training_sessions?:TrainingSession[];sklearn_review?:ShadowReview|null;checked_at:string;mode:"PAPER";unavailable:string[];portfolio:{closed:number;open:number;entries_today_utc:number;daily_ceiling:number;sum_r:number}|null;selector:{samples:number;minimum_samples:number;days:number;minimum_days:number;data_gates_met:boolean;status:string;generated_at:string}|null;agents:{agent:string;weight:number;weight_change:number|null;samples:number|null;brier_score:number}[];profile_generated_at?:string;asset_classes:{category:string;closed:number;open:number;win_rate:number|null;sum_r:number}[];rejections:{counts:{category:string;count:number}[];events_sampled:number;truncated:boolean;from:string|null;through:string|null;stale:boolean}|null};
const labels:Record<string,[string,string]>={CRYPTO:["عملات رقمية","Crypto"],STOCKS:["أسهم","Stocks"],FOREX:["عملات","Forex"],METALS:["معادن","Metals"],ENERGY:["طاقة","Energy"],COMMODITIES:["سلع","Commodities"],INDICES:["مؤشرات","Indices"],OTHER:["أخرى","Other"],CONCENTRATION:["تركّز الفئة","Category concentration"],OPEN_LIMIT:["حد المراكز المفتوحة","Open position limit"],DAILY_LIMIT:["السقف اليومي","Daily ceiling"],QUOTES:["أسعار قديمة أو غير متاحة","Stale or missing quotes"],CONFIDENCE:["ثقة غير كافية","Insufficient confidence"],RISK:["ضوابط المخاطر","Risk controls"],COUNCIL:["عدم تأكيد المجلس","Council did not confirm"],NO_SETUP:["غياب فرصة مؤهّلة","No qualified setup"],technical:["الوكيل الفني","Technical agent"],confidence:["وكيل الثقة","Confidence agent"]};
const fixed=(n:number|null|undefined,d=4)=>n==null?"—":n.toLocaleString("en-US",{maximumFractionDigits:d});
const time=(s:string|null|undefined)=>s?new Date(s).toLocaleString():"—";
export function TrainingPanel({language="ar"}:{language?:"ar"|"en"}){
 const ar=language==="ar";const [data,setData]=useState<Overview|null>(null);const [failed,setFailed]=useState(false);
 useEffect(()=>{
  let active=true;let controller:AbortController;
  const refresh=async()=>{
   controller?.abort();controller=new AbortController();
   try{
    const value=await atlasFetch<Overview>(apiPath("/api/runtime/training"),{credentials:"same-origin",cache:"no-store",signal:controller.signal});
    if(value.mode!=="PAPER"||!Array.isArray(value.agents)||!Array.isArray(value.asset_classes))throw new Error("Invalid overview");
    if(active){setData(value);setFailed(false);}
   }catch{if(active){setFailed(true);setData(null);}}
  };
  void refresh();const timer=setInterval(()=>void refresh(),30000);
  return()=>{active=false;clearInterval(timer);controller?.abort();};
 },[]);
 const text=(key:string)=>labels[key]?.[ar?0:1]??key;
 const p=data?.portfolio;const s=data?.selector;const r=data?.rejections;
 return <section id="training" className={"atlas-card atlas-secondary-zone "+styles.panel} dir={ar?"rtl":"ltr"} lang={language}>
  <h2>{ar?"متابعة تدريب أطلس":"ATLAS training monitor"} <small>PAPER · SHADOW</small></h2>
  {failed?<p role="alert">{ar?"بيانات التدريب غير متاحة حاليًا. يلزم حساب المالك.":"Training data unavailable. Owner access is required."}</p>:!data?<p role="status">{ar?"جارٍ تحميل نتائج التدريب…":"Loading training results…"}</p>:<>
   <p className={styles.muted}>{ar?"آخر فحص: ":"Last checked: "}<time dateTime={data.checked_at}>{time(data.checked_at)}</time> · {ar?"تحديث كل ٣٠ ثانية":"Refresh every 30 seconds"}</p>
   <div className={styles.metrics}>
    <article><span>{ar?"النتائج المغلقة":"Settled results"}</span><strong>{fixed(p?.closed,0)}</strong></article>
    <article><span>{ar?"المراكز المفتوحة":"Open positions"}</span><strong>{fixed(p?.open,0)}</strong></article>
    <article><span>{ar?"دخول اليوم بتوقيت UTC":"Today's entries (UTC)"}</span><strong>{p?p.entries_today_utc+" / "+p.daily_ceiling:"—"}</strong><small>{ar?"سقف، وليس عددًا إلزاميًا":"Ceiling, not a quota"}</small></article>
    <article><span>{ar?"مجموع العائد الورقي R":"Total paper return R"}</span><strong>{fixed(p?.sum_r)}</strong></article>
   </div>
   <h3>{ar?"جاهزية نموذج الاختيار":"Selector readiness"}</h3>
   {s?<div className={styles.gates}>
    <div><span>{ar?"نتائج صالحة":"Valid results"}</span><strong>{s.samples+" / "+s.minimum_samples}</strong><progress max={s.minimum_samples} value={Math.min(s.samples,s.minimum_samples)} aria-label={ar?"تقدم النتائج":"Results progress"}/></div>
    <div><span>{ar?"أيام دخول مختلفة UTC":"Distinct entry dates (UTC)"}</span><strong>{s.days+" / "+s.minimum_days}</strong><progress max={s.minimum_days} value={Math.min(s.days,s.minimum_days)} aria-label={ar?"تقدم الأيام":"Days progress"}/></div>
    <p>{s.status==="SHADOW_ONLY"?(ar?"التقييم التجريبي جاهز؛ القرار ما زال في وضع الظل":"Experimental evaluation ready; decisions remain shadow-only"):s.data_gates_met?(ar?"تحقق حد البيانات؛ النموذج ينتظر شروط التقييم":"Data minimum met; evaluation conditions still apply"):(ar?"بانتظار بيانات إضافية":"Waiting for more data")}<br/><small>{ar?"آخر تقرير: ":"Last report: "}{time(s.generated_at)} · {s.status}</small></p>
   </div>:<p>{ar?"تقرير النموذج غير متاح":"Selector report unavailable"}</p>}
   <PaperEvidence trades={data.paper_trades} sessions={data.training_sessions} review={data.sklearn_review} language={language} />
   <h3>{ar?"أوزان الوكلاء وجودة المعايرة":"Agent weights and calibration"}</h3>
   <p className={styles.muted}>{ar?"الوزن هو تأثير الوكيل في القرار، وليس احتمال نجاح. الفرق مقارنة ببداية اليوم UTC، محسوب من السجل. Brier: الأقل أفضل.":"Weight is influence in the decision, not a success probability. Changes are reconstructed from the journal against the start of today's UTC day. Lower Brier is better."}</p>
   <div className={styles.scroll}><table><thead><tr>{(ar?["الوكيل","الوزن","الفرق","الأمثلة","Brier"]:["Agent","Weight","Change","Examples","Brier"]).map(x=><th key={x} scope="col">{x}</th>)}</tr></thead><tbody>{data.agents.map(a=><tr key={a.agent}><th scope="row">{text(a.agent)}</th><td>{fixed(a.weight)}</td><td>{a.weight_change==null?"—":(a.weight_change>0?"+":"")+fixed(a.weight_change)}</td><td>{fixed(a.samples,0)}</td><td>{fixed(a.brier_score)}</td></tr>)}</tbody></table></div>
   {!data.agents.length&&<p>{ar?"ملف الأوزان غير متاح":"Weight profile unavailable"}</p>}
   <p className={styles.muted}>{ar?"تحديث الأوزان: ":"Weights updated: "}{time(data.profile_generated_at)}</p>
   <h3>{ar?"النتائج حسب فئة الأصول":"Results by asset class"}</h3>
   <div className={styles.scroll}><table><thead><tr>{(ar?["الفئة","مغلق","مفتوح","نسبة الربح","مجموع R"]:["Class","Closed","Open","Win rate","Sum R"]).map(x=><th key={x} scope="col">{x}</th>)}</tr></thead><tbody>{data.asset_classes.map(a=><tr key={a.category}><th scope="row">{text(a.category)}</th><td>{a.closed}</td><td>{a.open}</td><td>{a.win_rate==null?"—":fixed(a.win_rate*100,1)+"%"}</td><td>{fixed(a.sum_r)}</td></tr>)}</tbody></table></div>
   <h3>{ar?"أسباب عدم الدخول":"Reasons for no entry"}</h3>
   {r?<><p className={styles.muted}>{ar?"عينة حديثة محدودة من السجل؛ العدّ للأحداث وقد تتكرر الفرصة نفسها.":"Bounded recent journal sample; counts are events and may repeat the same opportunity."} {r.truncated&&(ar?"ليست إجمالي اليوم.":"Not a daily total.")}</p>
    <p>{time(r.from)} — {time(r.through)} · {r.events_sampled} {ar?"حدث مفحوص":"events reviewed"}</p>
    {r.stale&&<p role="status">{ar?"بيانات الفرص قديمة أو غير متاحة":"Opportunity data is stale or unavailable"}</p>}
    <ul className={styles.reasons}>{r.counts.map(x=><li key={x.category}><span>{text(x.category)}</span><strong>{x.count}</strong></li>)}</ul>
    {!r.counts.length&&<p>{ar?"لم تُسجّل أسباب رفض في هذه العينة":"No rejection reasons in this sample"}</p>}
   </>:<p>{ar?"سجل الفرص غير متاح":"Opportunity journal unavailable"}</p>}
   {data.unavailable.length>0&&<p role="status">{ar?"بعض المصادر غير متاحة؛ الشرطة تعني مجهولًا.":"Some sources are unavailable; a dash means unknown."}</p>}
   <p className={styles.muted}>{ar?"العوائد ورقية ومطبّعة بالمخاطر. السبريد مشمول؛ العمولة والرسوم مستثناة. النتائج تاريخية استكشافية ولا تثبت نجاحًا بنسبة ٨٠٪.":"Returns are risk-normalized paper results. Spread included; commissions and fees excluded. Historical exploratory results do not prove an 80% success rate."}</p>
  </>}
 </section>;
}
