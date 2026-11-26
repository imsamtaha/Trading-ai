"use client";
import { useCallback, useEffect, useState } from "react";
import { AtlasShell } from "@/components/layout/atlas-shell";
import { AccountConnection } from "@/features/trades/account-connection";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type Connection = { connected: boolean; account_type?: string | null; account_masked?: string | null; server?: string | null };
type Runtime = { demo_execution: boolean; learned_council_enabled: boolean; live_execution: string };
export default function ConnectPage() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [owner, setOwner] = useState(false);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [notice, setNotice] = useState("");
  const ar = language === "ar";
  const refresh = useCallback(async () => {
    try {
      const me = await atlasFetch<{ user: { role?: string } }>(apiPath("/api/me"), { credentials: "same-origin" });
      setSignedIn(true);
      const isOwner = me.user.role === "OWNER";
      setOwner(isOwner);
      setConnection(await atlasFetch<Connection>(apiPath("/api/mt5-demo/state"), { credentials: "same-origin" }));
      if (isOwner) setRuntime(await atlasFetch<Runtime>(apiPath("/api/runtime/status"), { credentials: "same-origin" }));
    } catch { setSignedIn(false); setConnection(null); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  async function toggle() {
    if (!runtime) return;
    setNotice("");
    try {
      const next = await atlasFetch<Runtime>(apiPath("/api/runtime/learned-council"), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !runtime.learned_council_enabled }),
      });
      setRuntime(next);
    } catch { setNotice(ar ? "تعذّر تغيير وضع المجلس. تأكّد من تفعيل تنفيذ Demo." : "Unable to change council mode. Enable Demo execution first."); }
  }
  return <AtlasShell language={language}><section className="atlas-connect-page" dir={ar ? "rtl" : "ltr"} lang={language}>
    <div className="atlas-language-row"><button onClick={() => setLanguage("ar")}>العربية</button><span>|</span><button onClick={() => setLanguage("en")}>EN</button></div>
    <header className="atlas-card"><span className="atlas-card-label">ATLAS × FxPro MT5</span>
      <h1>{ar ? "اربط حسابك بمجلس أطلس" : "Connect your account to ATLAS"}</h1>
      <p>{ar ? "صفحة مستقلة لربط MT5 ومتابعة حالة المجلس. الربط لا يرسل صفقة بحدّ ذاته." : "A dedicated MT5 connection and council status page. Connecting alone does not submit an order."}</p>
    </header>
    {signedIn === false && <section className="atlas-card"><p>{ar ? "سجّل دخولك أولاً لحماية حساب MT5." : "Sign in to protect your MT5 account."}</p><a href="/login" className="atlas-primary-button">{ar ? "تسجيل الدخول" : "Sign in"}</a></section>}
    {signedIn && <><AccountConnection language={language} onConnected={() => { void refresh(); }} />
      <section className="atlas-card"><h2>{ar ? "حالة الربط والمجلس" : "Connection and council status"}</h2>
        <p>{connection?.connected ? `${connection.account_type} · ${connection.account_masked} · ${connection.server}` : (ar ? "لم يتم ربط حساب MT5 بعد." : "No MT5 account connected yet.")}</p>
        {owner && runtime && <><p>{ar ? "مجلس Demo المتعلّم:" : "Learned Demo council:"} <strong>{runtime.learned_council_enabled && runtime.demo_execution ? (ar ? "مفعّل" : "Enabled") : (ar ? "متوقف" : "Stopped")}</strong></p>
          <button className="atlas-primary-button" type="button" onClick={() => void toggle()}>{runtime.learned_council_enabled ? (ar ? "إيقاف المجلس" : "Stop council") : (ar ? "تشغيل المجلس التجريبي" : "Start Demo council")}</button></>}
        <p>{ar ? "الحساب الحقيقي يحتاج اشتراكاً نشطاً تم تأكيد دفعه. التنفيذ الحقيقي مقفل حالياً على الخادم." : "A live account requires an active, verified paid subscription. Live execution is currently locked on the server."}</p>
        <a href="/subscribe">{ar ? "خطط الاشتراك" : "Subscription plans"}</a> · <a href="/dashboard">{ar ? "لوحة التداول والصفقات" : "Trading dashboard and positions"}</a> · <a href="/offline-contact.html">{ar ? "كود تواصل بلا إنترنت" : "Offline contact code"}</a>
        {notice && <p role="status">{notice}</p>}
      </section></>}
  </section></AtlasShell>;
}
