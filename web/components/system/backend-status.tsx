export type BackendState = "checking" | "online" | "offline" | "degraded";
const labels: Record<BackendState, string> = { checking: "Checking backend", online: "Backend online", offline: "Backend offline", degraded: "Backend degraded" };
export function BackendStatus({ status }: { status: BackendState }) {
  return <div role="status" className={`atlas-backend-status atlas-backend-status--${status}`}>{labels[status]}</div>;
}
