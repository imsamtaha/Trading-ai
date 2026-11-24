"use client";

import { useEffect, useState } from "react";
import { AgentBadge } from "@/components/system/agent-badge";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";

type GuardEvent = { decision_id?: string; status?: string; reason?: string | null };
type GuardStatus = { status?: string; last_event?: GuardEvent | null };
type Language = "ar" | "en";

const arabicStatus: Record<string, string> = {
  LOADING: "جارٍ التحميل", READY: "جاهز", APPROVED: "موافق عليه",
  BLOCKED: "محظور", EXECUTED: "منفّذ", FILLED: "منفّذ",
  WAITING_CONFIRMATION: "بانتظار التأكيد", EXPIRED: "منتهي الصلاحية",
  REJECTED: "مرفوض", UNKNOWN: "غير معروف",
};
const arabicReason: Record<string, string> = {
  "Demo execution is disabled.": "تنفيذ الصفقات التجريبية معطّل.",
  "Duplicate decision.": "القرار مكرّر.",
  "Council decision is WAIT.": "قرر المجلس الانتظار.",
  "Council confidence is below the execution threshold.": "ثقة المجلس أقل من حد التنفيذ.",
  "Council decision is stale or future-dated.": "قرار المجلس قديم أو تاريخه في المستقبل.",
  "MT5 account is not connected.": "حساب MT5 غير متصل.",
  "Fresh market price is unavailable.": "السعر الحالي غير متاح.",
};
const label = (value: string, language: Language) =>
  language === "ar" ? (arabicStatus[value] ?? "حالة غير معروفة") : value;
const reasonLabel = (value: string, language: Language) =>
  language === "ar" ? (arabicReason[value] ?? "تم منع التنفيذ لأسباب تتعلق بالحماية.") : value;

export function ExecutionAgentPanel({ language = "en" }: { language?: Language }) {
  const [status, setStatus] = useState("LOADING");
  const [events, setEvents] = useState<GuardEvent[]>([]);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      atlasFetch<GuardStatus>(apiPath("/api/execution-guard/status"), { credentials: "same-origin" }),
      atlasFetch<GuardEvent[]>(apiPath("/api/execution-guard/events"), { credentials: "same-origin" }),
    ]).then(([state, history]) => {
      if (!active) return;
      setStatus(state.status ?? "READY");
      setEvents(history.slice(0, 5));
    }).catch(() => { if (active) setUnavailable(true); });
    return () => { active = false; };
  }, []);
  const ar = language === "ar";
  return <section className="atlas-card atlas-feature-3d atlas-execution-agent" id="execution-agent" lang={language}>
    <h2 className="atlas-agent-title" dir={ar ? "rtl" : "ltr"}>{ar ? <><span>وكيل التنفيذ</span><AgentBadge /></> : <><AgentBadge /><span>Execution Agent</span></>}</h2>
    {unavailable ? <p className="atlas-empty-line">{ar ? "حالة التنفيذ غير متاحة حالياً" : "Execution status unavailable"}</p> : <>
      <p><span>{ar ? "حالة الحماية:" : "Guard status:"}</span> <strong>{label(status, language)}</strong></p>
      <p>{ar ? "تُراجع أوامر الحساب التجريبي قبل التنفيذ. أوامر الحساب الحقيقي غير مفعّلة." : "Demo decisions may auto-execute only after guard checks. Live decisions remain draft-only."}</p>
      {events.length > 0 ? <ul className="atlas-activity-list">
        {events.map((event, index) => <li key={`${event.decision_id ?? "event"}-${index}`}>
          <strong>{label(event.status ?? "UNKNOWN", language)}</strong>{event.decision_id ? ` · ${event.decision_id}` : ""}{event.reason ? ` · ${reasonLabel(event.reason, language)}` : ""}
        </li>)}
      </ul> : <p className="atlas-empty-line">{ar ? "لا توجد أحداث تنفيذ بعد" : "No execution events yet"}</p>}
    </>}
  </section>;
}
