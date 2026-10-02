"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";

type Language = "ar" | "en";

export function AccountConnection({ onConnected, language = "ar" }: { onConnected: () => void; language?: Language }) {
  const ar = language === "ar";
  const [type, setType] = useState<"DEMO" | "REAL">("DEMO");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("FxPro-MT5 Demo");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [liveEligible, setLiveEligible] = useState(false);
  useEffect(() => {
    let active = true;
    atlasFetch<{ user: { role?: string }; subscription?: { plan?: string; status?: string; expires_at?: string; billing_reference?: string } }>(apiPath("/api/me"), { credentials: "same-origin" })
      .then(({ user, subscription }) => {
        if (!active) return;
        const paid = subscription?.status === "ACTIVE" && ["STARTER", "PRO", "ELITE"].includes((subscription.plan || "").toUpperCase())
          && (subscription.billing_reference || "").startsWith("ATLAS-") && Date.parse(subscription.expires_at || "") > Date.now();
        setLiveEligible(user.role === "OWNER" || paid);
      }).catch(() => { if (active) setLiveEligible(false); });
    return () => { active = false; };
  }, []);
  async function connect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (type === "REAL" && !liveEligible) { setStatus(ar ? "الحساب الحقيقي يتطلب اشتراكاً مؤكداً وسارياً." : "A verified active subscription is required for a live account."); return; }
    setBusy(true); setStatus("");
    try {
      await atlasFetch(apiPath(type === "REAL" ? "/api/mt5-demo/connect-real" : "/api/mt5-demo/connect"), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login: Number(login), password, server, broker: "FxPro" }),
      });
      setPassword(""); setStatus(ar ? "تم ربط MT5" : "MT5 connected"); onConnected();
    } catch { setPassword(""); setStatus(ar ? "تعذّر الاتصال. تحقق من بيانات MT5." : "Unable to connect. Check your MT5 details."); }
    finally { setBusy(false); }
  }
  return <section className="atlas-card atlas-account-connection atlas-account-connection--premium" id="account-connection" dir={ar ? "rtl" : "ltr"}>
    <div className="atlas-connection-heading">
      <div className="atlas-connection-icon" aria-hidden="true">▥</div>
      <div><h2>{ar ? "ربط FxPro MT5" : "Connect FxPro MT5"}</h2><p>{ar ? "سجّل الدخول ثم اربط حسابك التجريبي أو الحقيقي" : "Sign in, then connect your demo or live account"}</p></div>
    </div>
    <form onSubmit={connect}>
      <label>{ar ? "نوع الحساب" : "Account type"}<select aria-label={ar ? "نوع الحساب" : "Account type"} value={type} onChange={(e) => { const next=e.target.value as "DEMO"|"REAL"; setType(next); setServer(next === "DEMO" ? "FxPro-MT5 Demo" : "FxPro-MT5 Live"); }}><option value="DEMO">{ar ? "تجريبي" : "Demo"}</option><option value="REAL">{ar ? "حقيقي" : "Live"}</option></select></label>
      <label>{ar ? "رقم MT5" : "MT5 login"}<input aria-label={ar ? "رقم MT5" : "MT5 login"} type="number" inputMode="numeric" required value={login} onChange={(e) => setLogin(e.target.value)} placeholder={ar ? "أدخل رقم MT5" : "Enter MT5 login"} /></label>
      <label>{ar ? "كلمة المرور" : "MT5 password"}<input aria-label={ar ? "كلمة المرور" : "MT5 password"} type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder={ar ? "أدخل كلمة المرور" : "Enter password"} /></label>
      <label>{ar ? "الخادم" : "MT5 server"}<input aria-label={ar ? "الخادم" : "MT5 server"} required value={server} onChange={(e) => setServer(e.target.value)} placeholder="FxPro-MT5 Demo" /></label>
      {type === "REAL" && !liveEligible && <p><a href="/subscribe">{ar ? "راجع خطط الاشتراك واطلب التفعيل" : "View subscription plans and request activation"}</a></p>}
      <button className="atlas-primary-button atlas-connect-button" type="submit" disabled={busy || (type === "REAL" && !liveEligible)}>{busy ? (ar ? "جارٍ الربط…" : "Connecting…") : (ar ? "ربط MT5" : "Connect MT5")}</button>
    </form>
    {status && <p role="status" className="atlas-connect-status">{status}</p>}
  </section>;
}
