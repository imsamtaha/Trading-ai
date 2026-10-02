"use client";
import { useEffect, useRef, useState } from "react";
import { atlasFetch, AtlasApiError } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type RuntimeState = {
  backend: string; demo_execution: boolean; learned_council_enabled: boolean; live_execution: string; restart_supported: boolean; instance_id?: string;
};
export default function RuntimePage() {
  const [runtime, setRuntime] = useState<RuntimeState | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Checking backend…");
  const [error, setError] = useState("");
  const alive = useRef(true);
  const mutating = useRef(false);
  const checking = useRef(false);
  const restarting = useRef(false);
  const restartOrigin = useRef<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  async function refresh() {
    if (checking.current || mutating.current) return;
    checking.current = true;
    const request = new AbortController();
    controller.current = request;
    try {
      const value = await atlasFetch<RuntimeState>(apiPath("/api/runtime/status"),
        { credentials: "same-origin", cache: "no-store", signal: request.signal }, 5000);
      if (!alive.current || mutating.current) return;
      if (value.backend !== "ONLINE" || typeof value.demo_execution !== "boolean" ||
          typeof value.restart_supported !== "boolean" || typeof value.live_execution !== "string")
        throw new Error("Invalid runtime status");
      if (restarting.current && (!value.instance_id || value.instance_id === restartOrigin.current)) {
        setRuntime(null); setMessage("Restarting backend… waiting for a new process.");
        return;
      }
      setRuntime(value);
      setMessage(restarting.current ? "Backend restarted successfully." : "Backend online.");
      restarting.current = false;
    } catch (e) {
      if (!alive.current || request.signal.aborted) return;
      setRuntime(null);
      if (e instanceof AtlasApiError && (e.status === 401 || e.status === 403)) {
        setError("Owner sign-in required."); setMessage("Access unavailable.");
      } else {
        setMessage(restarting.current ? "Restarting backend… waiting for recovery." : "Backend unreachable. Use the local launcher.");
      }
    } finally { checking.current = false; }
  }
  useEffect(() => {
    alive.current = true;
    void refresh();
    const interval = setInterval(() => { void refresh(); }, 5000);
    return () => { alive.current = false; clearInterval(interval); controller.current?.abort(); };
  }, []);
  async function change(action: "demo-execution" | "learned-council" | "restart") {
    if (!runtime || mutating.current || (action === "restart" && !runtime.instance_id)) return;
    if (action === "restart") restartOrigin.current = runtime.instance_id ?? null;
    mutating.current = true; controller.current?.abort();
    setBusy(true); setError("");
    setMessage(action === "restart" ? "Restart requested…" : "Updating demo permission…");
    try {
      const result = await atlasFetch<RuntimeState | { status: string }>(
        apiPath("/api/runtime/" + action), {
          method: "POST", credentials: "same-origin",
          headers: { "content-type": "application/json" },
          ...(action === "demo-execution" ? { body: JSON.stringify({ enabled: !runtime.demo_execution }) } : action === "learned-council" ? { body: JSON.stringify({ enabled: !runtime.learned_council_enabled }) } : {}),
        }, 10000);
      if (!alive.current) return;
      if (action === "restart") {
        if (!("status" in result) || result.status !== "RESTARTING") throw new Error("Invalid restart response");
        restarting.current = true; setRuntime(null); setMessage("Restarting backend… waiting for recovery.");
      } else {
        if (!("demo_execution" in result) || typeof result.demo_execution !== "boolean") throw new Error("Invalid runtime response");
        setRuntime(result); setMessage(action === "learned-council" ? (result.learned_council_enabled ? "Learned Demo council enabled." : "Learned Demo council stopped.") : (result.demo_execution ? "Demo orders enabled." : "Demo orders disabled."));
      }
    } catch {
      if (alive.current) { setRuntime(null); setError("Request failed. Refresh status before trying again."); }
    } finally { mutating.current = false; if (alive.current) setBusy(false); }
  }
  const ownerReady = Boolean(runtime) && !error;
  return <main className="atlas-runtime-page" lang="en">
    <section className="atlas-card atlas-runtime-box atlas-runtime-hero">
      <div>
        <span className="atlas-runtime-kicker">ATLAS OWNER</span>
        <h1>ATLAS Runtime</h1>
        <p className="atlas-runtime-subtitle">Owner controls · تحكّم المالك</p>
      </div>
      <div className={`atlas-runtime-access ${ownerReady ? "is-online" : "is-locked"}`}>
        <span className="atlas-runtime-access-dot" aria-hidden="true" />
        <div>
          <strong>{ownerReady ? "Owner access active" : "Owner access required"}</strong>
          <small>{ownerReady ? "Private runtime controls are available." : "Sign in with the owner account to unlock controls."}</small>
        </div>
      </div>
      <p className="atlas-runtime-message" role="status" aria-live="polite">{message}</p>
      {error && <p className="atlas-runtime-error" role="alert">{error}</p>}
    </section>

    <section className="atlas-card atlas-runtime-box">
      <div className="atlas-runtime-section-head">
        <div><span className="atlas-runtime-kicker">CONTROL</span><h2>Runtime Actions</h2></div>
        <span className="atlas-runtime-section-note">Demo-safe owner controls</span>
      </div>
      <div className="atlas-runtime-actions">
        <button className="atlas-primary-button atlas-runtime-action" type="button" role="switch"
          aria-label="Demo execution" aria-checked={runtime?.demo_execution ?? false}
          disabled={busy || !runtime} onClick={() => void change("demo-execution")}>
          <span>{runtime?.demo_execution ? "Stop demo orders" : "Start demo orders"}</span>
          <small>{runtime?.demo_execution ? "Demo execution is enabled" : "Enable guarded demo execution"}</small>
        </button>
        <button className="atlas-primary-button atlas-runtime-action" type="button"
          aria-label="Learned Demo council" aria-pressed={runtime?.learned_council_enabled ?? false}
          disabled={busy || !runtime?.demo_execution} onClick={() => void change("learned-council")}>
          <span>{runtime?.learned_council_enabled ? "Stop learned Demo council" : "Start learned Demo council"}</span>
          <small>Controls the scheduled council worker</small>
        </button>
        <button className="atlas-primary-button atlas-runtime-action" type="button" aria-label="Restart backend"
          disabled={busy || !runtime?.restart_supported || !runtime?.instance_id} onClick={() => void change("restart")}>
          <span>Restart backend</span>
          <small>Restart the private ATLAS API process</small>
        </button>
        <button className="atlas-runtime-action atlas-runtime-action--secondary" type="button" aria-label="Refresh status"
          disabled={busy} onClick={() => { setError(""); void refresh(); }}>
          <span>Refresh status</span>
          <small>Fetch current runtime state</small>
        </button>
      </div>
    </section>

    <section className="atlas-card atlas-runtime-box">
      <div className="atlas-runtime-section-head">
        <div><span className="atlas-runtime-kicker">EXECUTION</span><h2>Execution Status</h2></div>
        <span className="atlas-runtime-live-pill">{runtime?.live_execution ?? "UNKNOWN"}</span>
      </div>
      <div className="atlas-runtime-info-grid">
        <div className="atlas-runtime-info-item"><span>Live execution</span><strong>{runtime?.live_execution ?? "UNKNOWN"}</strong></div>
        <div className="atlas-runtime-info-item"><span>Demo orders</span><strong>{runtime?.demo_execution ? "ENABLED" : "DISABLED"}</strong></div>
        <div className="atlas-runtime-info-item"><span>Learned council</span><strong>{runtime?.learned_council_enabled ? "ENABLED" : "DISABLED"}</strong></div>
      </div>
      <p className="atlas-runtime-copy">The learned council runs on the scheduled Windows Demo worker when both demo switches are enabled. Existing positions remain open when stopped.</p>
    </section>

    <section className="atlas-card atlas-runtime-box">
      <div className="atlas-runtime-section-head">
        <div><span className="atlas-runtime-kicker">CONNECTION</span><h2>MT5 & Backend</h2></div>
      </div>
      <div className="atlas-runtime-links">
        <a className="atlas-runtime-link-card" href="/connect"><span>FxPro MT5 connection</span><small>Open connection status and account setup</small></a>
        <div className="atlas-runtime-note-card"><span>Backend note</span><small>Disabling orders does not close existing positions. A stopped backend needs the local Windows launcher.</small></div>
      </div>
    </section>

    <section className="atlas-card atlas-runtime-box atlas-runtime-footer">
      <a href="/dashboard">Dashboard</a>
      <span>•</span>
      <a href="/login">Owner sign-in</a>
    </section>
  </main>;
}
