"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type Monitor = {
  state: "ACTIVE" | "STALE" | "UNAVAILABLE";
  checked_at_utc?: string;
  components?: Record<string, {state: string; open_positions?: number}>;
};
const labels: Record<string, [string, string]> = {
  HEALTHY: ["متصل", "Healthy"], HTTPS_REACHABLE: ["متاح", "Reachable"],
  MT5_OFFLINE: ["غير متصل", "Disconnected"], ALGO_DISABLED: ["التداول الآلي متوقف", "Algo disabled"],
  ACCOUNT_MISMATCH: ["الحساب غير مطابق", "Account mismatch"],
  AUTH_REQUIRED: ["يحتاج تسجيل دخول", "Sign-in required"],
  HTTP_UNAVAILABLE: ["غير متاح", "Unavailable"], HTTPS_UNAVAILABLE: ["غير متاح", "Unavailable"],
  RUNNING_BUT_UNHEALTHY: ["الخدمة تعمل والفحص فشل", "Running but unhealthy"],
  MONITOR_BLOCKED: ["فحص الرابط محجوب", "Monitor blocked"],
};
export function ServerHealth({language}: {language: "ar" | "en"}) {
  const [monitor, setMonitor] = useState<Monitor | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const controllers = new Set<AbortController>();
    async function refresh() {
      const controller = new AbortController();
      controllers.add(controller);
      try {
        const result = await atlasFetch<{server_monitor?: Monitor}>(apiPath("/api/runtime/status"),
          {cache: "no-store", signal: controller.signal}, 10000);
        if (active) { setMonitor(result.server_monitor ?? null); setFailed(false); }
      } catch { if (active) setFailed(true); }
      finally { controllers.delete(controller); }
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 30000);
    return () => { active = false; clearInterval(timer); controllers.forEach(c => c.abort()); };
  }, []);
  if (!monitor) return null;
  const ar = language === "ar";
  const state = failed ? "STALE" : monitor.state;
  const title = state === "ACTIVE" ? (ar ? "المراقبة فعّالة" : "Monitor active")
    : state === "STALE" ? (ar ? "بيانات المراقبة قديمة" : "Monitor data is stale")
    : (ar ? "المراقبة غير متاحة" : "Monitor unavailable");
  const names: Record<string, string> = {
    backend: ar ? "الخادم" : "Backend", frontend: ar ? "الواجهة" : "Frontend",
    public_route: ar ? "الرابط" : "Public link", mt5: "MT5"
  };
  return <section className="atlas-card" aria-label={ar ? "استقرار خادم أطلس" : "ATLAS server stability"}>
    <h2>{ar ? "استقرار خادم أطلس" : "ATLAS server stability"}</h2>
    <p role="status">{title}</p>
    {monitor.checked_at_utc && <p>{ar ? "آخر فحص" : "Last check"}: <time dateTime={monitor.checked_at_utc}>{new Date(monitor.checked_at_utc).toLocaleString(ar ? "ar-LB" : "en-GB")}</time></p>}
    {state === "ACTIVE" && Object.entries(monitor.components ?? {}).map(([key,item]) =>
      <p key={key}>{names[key] ?? key}: {labels[item.state]?.[ar ? 0 : 1] ?? (ar ? "يحتاج فحص" : "Needs attention")}</p>)}
    {state === "ACTIVE" && monitor.components?.mt5?.open_positions !== undefined &&
      <p>{ar ? "الصفقات المفتوحة" : "Open positions"}: {monitor.components.mt5.open_positions} / 3</p>}
    <small>{ar ? "تستعيد المراقبة الخدمات المتوقفة تلقائيًا. انقطاع الإنترنت الكامل يحتاج اتصالًا احتياطيًا." : "Stopped services recover automatically. A full internet outage needs a backup connection."}</small>
  </section>;
}

