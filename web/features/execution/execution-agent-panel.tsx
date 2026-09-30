"use client";

import { useEffect, useState } from "react";
import { AgentBadge } from "@/components/system/agent-badge";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";

type GuardEvent = { decision_id?: string; status?: string; reason?: string | null };
type GuardStatus = { status?: string; last_event?: GuardEvent | null };
type RuntimeStatus = {
  backend: "ONLINE" | "OFFLINE";
  demo_execution: boolean;
  live_execution: "LOCKED";
  restart_supported: boolean;
};

export function ExecutionAgentPanel() {
  const [status, setStatus] = useState("LOADING");
  const [events, setEvents] = useState<GuardEvent[]>([]);
  const [unavailable, setUnavailable] = useState(false);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [runtimeBusy, setRuntimeBusy] = useState(false);
  const [runtimeMessage, setRuntimeMessage] = useState("");

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
    atlasFetch<RuntimeStatus>(apiPath("/api/runtime/status"), { credentials: "same-origin" })
      .then((state) => { if (active) setRuntime(state); })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  async function toggleDemoExecution() {
    if (!runtime || runtimeBusy) return;
    setRuntimeBusy(true);
    setRuntimeMessage("");
    try {
      const next = await atlasFetch<RuntimeStatus>(apiPath("/api/runtime/demo-execution"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !runtime.demo_execution }),
      });
      setRuntime(next);
    } catch {
      setRuntimeMessage("Runtime update failed");
    } finally {
      setRuntimeBusy(false);
    }
  }

  async function restartBackend() {
    if (!runtime?.restart_supported || runtimeBusy) return;
    setRuntimeBusy(true);
    setRuntimeMessage("");
    try {
      const result = await atlasFetch<{ status: string }>(apiPath("/api/runtime/restart"), {
        method: "POST",
        credentials: "same-origin",
      });
      setRuntimeMessage(result.status);
    } catch {
      setRuntimeMessage("Restart request failed");
    } finally {
      setRuntimeBusy(false);
    }
  }

  return <section className="atlas-card atlas-feature-3d atlas-execution-agent" id="execution-agent">
    <h2 className="atlas-card-title-left">EXECUTION AGENT <AgentBadge /></h2>
    {!unavailable && <>
      <p>Guard status: <strong>{status}</strong></p>
      <p>Demo decisions may auto-execute only after guard checks. Live decisions remain draft-only.</p>
      {events.length > 0 ? <ul className="atlas-activity-list">
        {events.map((event, index) => <li key={`${event.decision_id ?? "event"}-${index}`}>
          <strong>{event.status ?? "UNKNOWN"}</strong>{event.decision_id ? ` · ${event.decision_id}` : ""}{event.reason ? ` · ${event.reason}` : ""}
        </li>)}
      </ul> : <p className="atlas-empty-line">No execution events yet</p>}
    </>}
    {runtime && <div className="atlas-runtime-controls" aria-label="ATLAS Runtime Control">
      <div className="atlas-runtime-status-row">
        <span>Backend <strong>{runtime.backend}</strong></span>
        <span>Live Execution <strong>{runtime.live_execution}</strong></span>
      </div>
      <div className="atlas-runtime-actions">
        <button
          type="button"
          className="atlas-secondary-button"
          aria-pressed={runtime.demo_execution}
          disabled={runtimeBusy}
          onClick={toggleDemoExecution}
        >Demo Execution {runtime.demo_execution ? "ON" : "OFF"}</button>
        <button
          type="button"
          className="atlas-secondary-button"
          disabled={runtimeBusy || !runtime.restart_supported}
          onClick={restartBackend}
        >Restart Backend</button>
      </div>
      {runtimeMessage && <p className="atlas-runtime-message" role="status">{runtimeMessage}</p>}
    </div>}
  </section>;
}
