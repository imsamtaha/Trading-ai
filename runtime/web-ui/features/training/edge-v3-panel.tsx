"use client";
import {useEffect,useState} from "react";
import {atlasFetch} from "@/lib/api/client";
import {apiPath} from "@/lib/api/config";
import styles from "./training-panel.module.css";
type Card={observations:number;mean_net_r:number;expectancy_lower_r:number;status:string};
type Evidence={stage:"RESEARCH_ONLY";decision:"ABSTAIN";report_state:"UNAVAILABLE"|"STALE"|"LOCAL_RESEARCH_REPORT";broker_execution_allowed:false;live_activation_allowed:false;worker_verified:false;sample_count?:number;input_kind?:string;generated_at?:string;cost_stress?:Record<string,Card>};
function valid(value:Evidence){
 if(!value||value.stage!=="RESEARCH_ONLY"||value.decision!=="ABSTAIN"||value.broker_execution_allowed!==false||value.live_activation_allowed!==false||value.worker_verified!==false||!["UNAVAILABLE","STALE","LOCAL_RESEARCH_REPORT"].includes(value.report_state))return false;
 if(value.cost_stress&&Object.values(value.cost_stress).some(c=>!Number.isFinite(c.mean_net_r)||!Number.isFinite(c.expectancy_lower_r)))return false;
 return true;
}
export function EdgeV3Panel(){
 const [ar,setAr]=useState(true),[data,setData]=useState<Evidence|null>(null),[failed,setFailed]=useState(false),[attempt,setAttempt]=useState(0);
 useEffect(()=>{const controller=new AbortController();setData(null);setFailed(false);
  void atlasFetch<Evidence>(apiPath("/api/runtime/edge-v3"),{credentials:"same-origin",cache:"no-store",signal:controller.signal})
   .then(value=>{if(!valid(value))throw new Error("Invalid research projection");if(!controller.signal.aborted)setData(value);})
   .catch(()=>{if(!controller.signal.aborted)setFailed(true);});
  return()=>controller.abort();
 },[attempt]);
 return <section className={"atlas-card "+styles.panel} aria-label="Council v3 research evidence" dir={ar?"rtl":"ltr"} lang={ar?"ar":"en"}>
  <header><h2>ATLAS Council v3 · Edge-First</h2><button type="button" onClick={()=>setAr(!ar)}>{ar?"English":"العربية"}</button></header>
  <p><strong>{ar?"بحث فقط · القرار الافتراضي: امتناع":"Research only · Default: ABSTAIN"}</strong></p>
  <p>{ar?"هاللوحة ما بتفعّل تداول ولا بتغيّر أوزان المجلس. وجود كود أو تقرير ما بيثبت أفضلية أو أرباح.":"This panel cannot activate trading or change Council weights. Code and reports alone do not establish edge or profit."}</p>
  {failed?<p role="alert">{ar?"دليل v3 مش متاح. تأكّد من حساب المالك والخدمة.":"v3 evidence unavailable. Verify owner access and backend service."}</p>:!data?<p role="status">{ar?"عم نتحقّق من التقرير…":"Checking research report…"}</p>:<>
   <p>{ar?"حالة التقرير: ":"Report state: "}<strong>{data.report_state}</strong></p>
   {data.report_state==="UNAVAILABLE"?<p>{ar?"بعد ما في تقرير تقييم صالح. ما رح نعرض أرقام افتراضية.":"No valid evaluation report is available. No placeholder performance is shown."}</p>:<>
    <p>{ar?"نوع البيانات: ":"Input provenance: "}{data.input_kind||"UNVERIFIED_INPUT"}</p>
    <p>{ar?"قرارات التقييم: ":"Evaluation decisions: "}{data.sample_count??"—"}</p>
    <div className={styles.scroll}><table><caption>{ar?"العائد R لكل قرار، مش عائد حساب حي":"R per decision, not live account returns"}</caption><thead><tr><th>{ar?"ضغط الكلفة":"Cost stress"}</th><th>{ar?"المتوسط R":"Mean R"}</th><th>{ar?"الحد الأدنى R":"Lower bound R"}</th></tr></thead><tbody>{["1.0","1.5","2.0"].map(scale=><tr key={scale}><th scope="row">{scale}×</th><td>{data.cost_stress?.[scale]?.mean_net_r.toFixed(4)??"—"}</td><td>{data.cost_stress?.[scale]?.expectancy_lower_r.toFixed(4)??"—"}</td></tr>)}</tbody></table></div>
   </>}
   <p>{ar?"STC-04 وSTC-09: المراجعة بعدا معلّقة. تشغيل عامل v3: غير مثبت.":"STC-04 and STC-09: reviews pending. Running v3 worker: unverified."}</p>
  </>}
  <button type="button" onClick={()=>setAttempt(n=>n+1)}>{ar?"تحقّق من جديد":"Check again"}</button>
 </section>;
}
