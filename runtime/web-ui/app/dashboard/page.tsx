"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { getDashboardState } from "@/lib/api/dashboard";
import { AtlasApiError } from "@/lib/api/client";
import type { DashboardViewModel } from "@/lib/api/types";
import { PositionsPanel } from "@/features/trades/positions-panel";
import { RiskPanel } from "@/features/risk/risk-panel";
import { ActivityPanel } from "@/features/activity/activity-panel";
import styles from "./shield.module.css";

const site = "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/";
const views = [
  ["overview", "Paper portfolio", "المحفظة الورقية"],
  ["market", "Market data", "بيانات السوق"],
  ["trader", "Paper trader", "التداول الورقي"],
  ["training", "Council training", "تدريب المجلس"],
  ["workspace", "Saved workspace", "مساحة العمل المحفوظة"],
  ["connections", "Connections", "مركز الربط"],
] as const;

export default function DashboardPage() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [data, setData] = useState<DashboardViewModel | null>(null);
  const [status, setStatus] = useState<"loading" | "signedOut" | "error" | "ready">("loading");
  const [attempt, setAttempt] = useState(0);
  const ar = language === "ar";

  useEffect(() => {
    try { if (localStorage.getItem("atlas-dashboard-language") === "en") setLanguage("en"); } catch {}
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getDashboardState(controller.signal).then(result => {
      if (!controller.signal.aborted) { setData(result); setStatus("ready"); }
    }).catch(error => {
      if (!controller.signal.aborted) setStatus(error instanceof AtlasApiError && error.status === 401 ? "signedOut" : "error");
    });
    return () => controller.abort();
  }, [attempt]);

  function switchLanguage() {
    const next = ar ? "en" : "ar";
    setLanguage(next);
    try { localStorage.setItem("atlas-dashboard-language", next); } catch {}
  }

  return <main className={styles.center} lang={language} dir={ar ? "rtl" : "ltr"}>
    <header className={styles.bar}>
      <strong lang="en">ATLAS INTELLIGENCE</strong>
      <button onClick={switchLanguage} lang={ar ? "en" : "ar"}>{ar ? "English" : "العربية"}</button>
    </header>
    <section className={styles.hero}>
      <Image src="/atlas-tiger-shield.webp" width={480} height={360} alt="" priority />
      <div>
        <h1>{ar ? "مركز قيادة أطلس" : "Tiger Shield Command Center"}</h1>
        <p>{ar ? "راجع المحفظة الورقية، وحلّل الأسواق، واختبر قرارات المجلس." : "Review your paper portfolio, inspect markets, and test Council decisions."}</p>
        <a className={styles.primary} href={site + "#overview"}>{ar ? "افتح المحفظة الورقية" : "Open paper portfolio"}</a>
      </div>
    </section>
    <nav className={styles.views} aria-label={ar ? "مساحة العمل" : "Workspace"}>
      {views.map(([hash, en, arabic]) => <a key={hash} href={site + "#" + hash}>{ar ? arabic : en}</a>)}
    </nav>
    <section className={styles.account} aria-labelledby="account-title">
      <header><h2 id="account-title">{ar ? "حالة الحساب" : "Account status"}</h2><a href="/connect">{ar ? "إدارة الاتصال" : "Manage connection"}</a></header>
      <div role="status">
        {status === "loading" && (ar ? "جارٍ تحميل الحساب…" : "Loading account…")}
        {status === "signedOut" && <a href="/login">{ar ? "سجّل الدخول لعرض حسابك" : "Sign in to view your account"}</a>}
        {status === "error" && <>{ar ? "تعذّر تحميل بيانات الحساب. " : "Account data is unavailable. "}<button onClick={() => { setStatus("loading"); setAttempt(n => n + 1); }}>{ar ? "إعادة المحاولة" : "Retry"}</button></>}
        {status === "ready" && (data?.connection === "connected" ? (ar ? "الحساب متصل" : "Account connected") : (ar ? "الحساب غير متصل" : "Account disconnected"))}
      </div>
    </section>
    {data?.connection === "connected" && <div className={styles.panels}>
      <PositionsPanel positions={data.positions} available language={language} />
      <RiskPanel risk={data.risk} language={language} />
      <ActivityPanel events={data.activity} language={language} />
    </div>}
  </main>;
}
