"use client";
import { useEffect, useState, type ReactElement } from "react";
import { getDashboardState } from "../../lib/api/dashboard";
import { requestJson } from "../../lib/api/client";
export type BackendStatusState = "checking" | "online" | "offline" | "degraded";
export function resolveBackendStatus(healthOk: boolean, accountOk: boolean): BackendStatusState { return !healthOk ? "offline" : accountOk ? "online" : "degraded"; }
const LABELS: Record<BackendStatusState, string> = { checking: "Checking backend", online: "Backend online", offline: "Backend offline", degraded: "Backend degraded" };
export function BackendStatus({ status }: { status: BackendStatusState }): ReactElement { return <span className={`atlas-backend-status atlas-backend-status--${status}`} role="status"><i aria-hidden="true" />{LABELS[status]}</span>; }
export function LiveBackendStatus(): ReactElement {
  const [status, setStatus] = useState<BackendStatusState>("checking");
  useEffect(() => { let live = true; Promise.allSettled([requestJson<{status?: string}>("/health", { timeoutMs: 5000 }), getDashboardState()]).then(([health, account]) => { if (!live) return; setStatus(resolveBackendStatus(health.status === "fulfilled", account.status === "fulfilled" && account.value.connection === "online")); }); return () => { live = false; }; }, []);
  return <BackendStatus status={status} />;
}
