"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type RequestRow = { reference: string; email: string; plan_id: string; amount_usd: number; created_at: string };
export default function WhishAdminPage() {
  const [rows, setRows] = useState<RequestRow[]>([]);
  const [status, setStatus] = useState("Loading owner review queue…");
  const [verified, setVerified] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  async function load() {
    try {
      const result = await atlasFetch<{ requests: RequestRow[] }>(apiPath("/billing/whish/admin/requests"), { credentials: "same-origin" });
      setRows(result.requests); setStatus(result.requests.length ? "" : "No pending Whish requests.");
    } catch { setStatus("Owner sign-in required. Only the verified ATLAS admin account may review subscriptions."); }
  }
  useEffect(() => { void load(); }, []);
  async function approve(reference: string) {
    if (!verified.includes(reference)) return;
    setBusy(true); setStatus("");
    try {
      await atlasFetch(apiPath(`/billing/whish/admin/${reference}/approve`), { method: "POST", credentials: "same-origin" });
      setVerified((old) => old.filter((item) => item !== reference));
      await load();
      setStatus(`${reference} approved for 30 days.`);
    } catch { setStatus("Approval failed. Verify your admin session and review the request again."); }
    finally { setBusy(false); }
  }
  return <main className="atlas-page"><section className="atlas-card">
    <h1>Whish owner review</h1>
    <p>Check each payment directly in your Whish account before approving. An email notification, when configured, links here; receipt submission alone never activates ATLAS.</p>
    {rows.map((row) => <article className="atlas-card" key={row.reference}>
      <h2>{row.reference}</h2><p>{row.email} · {row.plan_id} · ${row.amount_usd} USD</p><p>{row.created_at}</p>
      <label><input type="checkbox" checked={verified.includes(row.reference)} onChange={(e) => setVerified((old) => e.target.checked ? [...old, row.reference] : old.filter((item) => item !== row.reference))} /> I verified the Whish transfer independently</label>
      <button className="atlas-primary-button" type="button" disabled={busy || !verified.includes(row.reference)} onClick={() => approve(row.reference)}>Approve subscription</button>
    </article>)}
    {status && <p role="status">{status}</p>}
  </section></main>;
}
