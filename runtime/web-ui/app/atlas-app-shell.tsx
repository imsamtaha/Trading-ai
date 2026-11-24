"use client";
import { useEffect, useState } from "react";
import { AtlasShell } from "@/components/layout/atlas-shell";
import { ServerHealth } from "@/components/system/server-health";
import { BackendStatus, type BackendState } from "@/components/system/backend-status";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { AccountConnection } from "@/features/trades/account-connection";
import { ManualTrading } from "@/features/trades/manual-trading";
import { getDashboardState } from "@/lib/api/dashboard";
import { getCandles } from "@/lib/api/market";
import { getMarketBriefing, type Headline } from "@/lib/api/briefing";
import { atlasFetch, AtlasApiError } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
import { mapDashboardState } from "@/lib/api/mappers";
import type { Candle, DashboardViewModel } from "@/lib/api/types";

const unavailable = mapDashboardState({ status: "OFFLINE" });
const preview = mapDashboardState({ status: "UNKNOWN" });

export function AtlasAppShell({ refreshMs = 30000, timeoutMs = 12000 }: { refreshMs?: number; timeoutMs?: number } = {}) {
  const [state, setState] = useState<DashboardViewModel>(unavailable);
  const [backend, setBackend] = useState<BackendState>("checking");
  const [sessionRequired, setSessionRequired] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [symbol, setSymbol] = useState("XAUUSD");
  const [timeframe, setTimeframe] = useState("1h");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [briefingAvailable, setBriefingAvailable] = useState(false);
  const [chartStatus, setChartStatus] = useState("Loading market data…");

  useEffect(() => {
    let active = true;
    const controllers = new Set<AbortController>();

    async function refresh() {
      const controller = new AbortController();
      controllers.add(controller);
      const [health, dashboard] = await Promise.allSettled([
        atlasFetch<{ status?: string }>(apiPath("/health"), { cache: "no-store", signal: controller.signal }, timeoutMs),
        getDashboardState(controller.signal, timeoutMs),
      ]);
      controllers.delete(controller);
      if (!active) return;

      const healthy = health.status === "fulfilled" && health.value.status === "healthy";
      if (dashboard.status === "rejected" && dashboard.reason instanceof AtlasApiError && dashboard.reason.status === 401) {
        setState(preview);
        setSessionRequired(true);
        setBackend(healthy ? "online" : "offline");
        return;
      }

      setSessionRequired(false);
      if (dashboard.status === "fulfilled" && healthy) {
        setState(dashboard.value.connection === "connected" ? dashboard.value : { ...dashboard.value, connection: "unknown" });
        setBackend("online");
      } else {
        setState(unavailable);
        setBackend(healthy ? "degraded" : "offline");
      }
    }

    void refresh();
    const interval = setInterval(() => { void refresh(); }, refreshMs);
    return () => {
      active = false;
      clearInterval(interval);
      controllers.forEach((controller) => controller.abort());
    };
  }, [refreshMs, timeoutMs, refreshKey]);

  useEffect(() => {
    let active = true;
    setHeadlines([]);
    setBriefingAvailable(false);
    getMarketBriefing(language)
      .then((items) => { if (active) { setHeadlines(items); setBriefingAvailable(true); } })
      .catch(() => { if (active) { setHeadlines([]); setBriefingAvailable(false); } });
    return () => { active = false; };
  }, [language]);

  useEffect(() => {
    let active = true;
    async function refreshChart() {
      try {
        const series = await getCandles(symbol, timeframe, 120, sessionRequired);
        if (active) {
          setCandles(series);
          setChartStatus(series.length ? "" : "Market data unavailable");
        }
      } catch {
        if (active) {
          setCandles([]);
          setChartStatus("Market data unavailable");
        }
      }
    }

    setCandles([]);
    setChartStatus("Loading market data…");
    void refreshChart();
    const interval = setInterval(() => { void refreshChart(); }, 60000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [symbol, timeframe, sessionRequired]);

  return <AtlasShell language={language}>
    <section data-testid="atlas-app-shell" className="atlas-app-workspace" lang={language} dir={language === "ar" ? "rtl" : "ltr"}>
      <div className="atlas-utility-row">
        <div className="atlas-language-row" aria-label="Language">
          <button type="button" className={language === "ar" ? "is-active" : ""} onClick={() => setLanguage("ar")}>العربية</button>
          <span>|</span>
          <button type="button" className={language === "en" ? "is-active" : ""} onClick={() => setLanguage("en")}>EN</button>
        </div>
        <div className="atlas-utility-status">
          <span className="atlas-paper-pill">PAPER MODE</span>
          <BackendStatus status={backend} language={language} />
        </div>
      </div>

      {!sessionRequired && <ServerHealth language={language} />}

      <nav className="atlas-connection-link" aria-label={language === "ar" ? "روابط مساحة العمل" : "Workspace links"}>
        <a href="/connect">{language === "ar" ? "ربط MT5 للبيانات" : "Connect MT5 data"}</a>
        <span>·</span>
        <a href="/subscribe">{language === "ar" ? "الاشتراكات" : "Subscriptions"}</a>
        <span>·</span>
        <a href="/offline-contact.html">{language === "ar" ? "تواصل" : "Contact"}</a>
      </nav>

      {sessionRequired && <main className="atlas-auth-required atlas-card atlas-auth-gate">
        <span className="atlas-auth-gate-badge">{language === "ar" ? "مساحة خاصة" : "PRIVATE WORKSPACE"}</span>
        <h2>{language === "ar" ? "استكشف أطلس" : "Explore ATLAS"}</h2>
        <p>{language === "ar"
          ? "سجّل الدخول للوصول إلى لوحة أطلس الخاصة، بيانات الجلسة، ومختبر التداول الورقي."
          : "Sign in to access your private ATLAS dashboard, session data, and Paper workspace."}</p>
        <div className="atlas-auth-gate-actions">
          <a className="atlas-primary-button" href="/login?returnTo=%2Fdashboard">
            {language === "ar" ? "تسجيل الدخول" : "Secure sign in"}
          </a>
          <span>{language === "ar" ? "المعاينة العامة تبقى للقراءة فقط." : "Public preview remains read-only."}</span>
        </div>
      </main>}

      {!sessionRequired && state.connection !== "connected" && <AccountConnection language={language} onConnected={() => setRefreshKey((key) => key + 1)} />}

      {!sessionRequired && state.connection === "connected" && state.account.mode === "DEMO" &&
        <ManualTrading key={refreshKey} language={language} />}

      {!sessionRequired && state.connection === "connected" && state.account.mode === "REAL" &&
        <section className="atlas-card atlas-paper-safety-banner" role="status">
          <strong>{language === "ar" ? "وضع الورق فقط" : "Paper-only workspace"}</strong>
          <p>{language === "ar"
            ? "بيانات السوق متاحة للتحليل، لكن أدوات إرسال أوامر الوسيط غير متاحة في هذه اللوحة."
            : "Market data remains available for analysis, but broker-order controls are unavailable in this workspace."}</p>
        </section>}

      {!sessionRequired && !state.entitlements?.tradingIntelligence &&
        <section className="atlas-card atlas-subscription-gate">
          <h2>{language === "ar" ? "اشتراك أطلس" : "ATLAS subscription"}</h2>
          <p>{language === "ar" ? "اختر الخطة المناسبة" : "Choose the plan that fits you"}</p>
          <a className="atlas-primary-button" href="/subscribe">{language === "ar" ? "عرض الخطط" : "View plans"}</a>
        </section>}

      {chartStatus && <span role="status" className="atlas-chart-status">{chartStatus}</span>}

      <DashboardScreen
        state={state}
        candles={candles}
        symbol={symbol}
        timeframe={timeframe}
        assistantAvailable={!sessionRequired && state.entitlements?.tradingIntelligence === true}
        assistantLockedHref={sessionRequired ? "/login?returnTo=%2Fdashboard" : "/subscribe"}
        intelligenceAvailable={!sessionRequired && state.entitlements?.tradingIntelligence === true}
        language={language}
        signals={state.signals ?? []}
        activity={state.activity ?? []}
        headlines={headlines}
        briefingAvailable={briefingAvailable}
        onMarketChange={(nextSymbol, nextTimeframe) => {
          setSymbol(nextSymbol);
          setTimeframe(nextTimeframe);
        }}
      />
    </section>
  </AtlasShell>;
}
