"use client";

import { useEffect, useState } from "react";
import { AgentBadge } from "@/components/system/agent-badge";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";

type GuardEvent = { decision_id?: string; status?: string; reason?: string | null };
type GuardStatus = { status?: string; last_event?: GuardEvent | null };

export function ExecutionAgentPanel() {
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

  return <section className="atlas-card atlas-feature-3d atlas-execution-agent" id="execution-agent">
    <span className="atlas-card-label">Execution Guard</span>
    <h2>EXECUTION AGENT <AgentBadge /></h2>
    {unavailable ? <p className="atlas-empty-line">Execution Guard unavailable</p> : <>
      <p>Guard status: <strong>{status}</strong></p>
      <p>Demo decisions may auto-execute only after guard checks. Live decisions remain draft-only.</p>
      {events.length > 0 ? <ul className="atlas-activity-list">
        {events.map((event, index) => <li key={`${event.decision_id ?? "event"}-${index}`}>
          <strong>{event.status ?? "UNKNOWN"}</strong>{event.decision_id ? ` · ${event.decision_id}` : ""}{event.reason ? ` · ${event.reason}` : ""}
        </li>)}
      </ul> : <p className="atlas-empty-line">No execution events yet</p>}
    </>}
  </section>;
}
