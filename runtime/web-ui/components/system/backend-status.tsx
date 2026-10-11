export type BackendState = "checking" | "online" | "offline" | "degraded";
const labels: Record<"ar" | "en", Record<BackendState, string>> = {
  en: { checking: "Checking backend", online: "Backend online", offline: "Backend offline", degraded: "Backend degraded" },
  ar: { checking: "جارٍ فحص الخادم", online: "الخادم متصل", offline: "الخادم غير متصل", degraded: "الخادم غير مستقر" },
};
export function BackendStatus({ status, language = "en" }: { status: BackendState; language?: "ar" | "en" }) {
  return <div role="status" className={`atlas-backend-status atlas-backend-status--${status}`}>{labels[language][status]}</div>;
}
