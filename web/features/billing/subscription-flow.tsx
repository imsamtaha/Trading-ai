"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type Plan = { id: string; name: string; monthly_price: number; features: string[] };
export function SubscriptionFlow() {
  const [email, setEmail] = useState<string | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [status, setStatus] = useState("");
  const [payment, setPayment] = useState<{ reference: string; recipient?: string; phone?: string; support?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([
      atlasFetch<{ user: { email: string } }>(apiPath("/api/me"), { credentials: "same-origin" }),
      atlasFetch<{ plans: Plan[] }>(apiPath("/billing/plans")),
    ]).then(([me, catalog]) => { if (active) { setEmail(me.user.email); setPlans(catalog.plans.filter(p => p.id !== "free")); } })
      .catch(() => { if (active) setStatus("Sign in with Google to request a subscription."); });
    return () => { active = false; };
  }, []);
  async function request(plan: Plan) {
    if (!email) return;
    setBusy(true); setStatus("");
    try {
      const result = await atlasFetch<{ reference: string; status: string; recipient?: string; phone?: string; support?: string }>(apiPath(`/billing/whish/${plan.id}/request`), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setPayment(result);
      setStatus(`${result.reference}: pending owner review. Payment requests do not activate ATLAS Trading Intelligence.`);
    } catch { setStatus("Unable to request Whish review. Check the payment method and your session."); }
    finally { setBusy(false); }
  }
  return <section className="atlas-card atlas-subscription-flow">
    <h1>ATLAS subscription via Whish</h1>
    <p>Send payment using the verified Whish details, then request review. Only the owner at imsamtaha.ai@gmail.com can confirm access. MT5 account monitoring is separate.</p>
    {!email && <a className="atlas-primary-button" href="/login">Sign in with Google</a>}
    <div className="atlas-plan-grid">{plans.map((plan) => <article className="atlas-card" key={plan.id}>
      <h2>{plan.name}</h2><strong>${plan.monthly_price} USD / month</strong>
      <ul>{plan.features.map((feature) => <li key={feature}>{feature}</li>)}</ul>
      <button type="button" className="atlas-primary-button" disabled={busy} onClick={() => request(plan)}>Request {plan.name.replace(/^ATLAS /, "")}</button>
    </article>)}</div>
    {payment && <aside className="atlas-card"><h2>Whish payment details</h2><p>Recipient: {payment.recipient || "Contact support"}</p><p>Phone: {payment.phone || "Contact support"}</p><p>Support: {payment.support || "Contact support"}</p><p>Use your reference when sending proof of payment. Only the owner confirms access.</p><a className="atlas-primary-button" href={`mailto:imsamtaha.ai@gmail.com?subject=${encodeURIComponent(`ATLAS Whish ${payment.reference}`)}&body=${encodeURIComponent(`Reference: ${payment.reference}\nAccount: ${email}\nPlease attach your Whish receipt.`)}`}>Email payment proof to owner</a></aside>}
    {status && <p role="status">{status}</p>}
  </section>;
}
