"use client";
import { useEffect, useState } from "react";
import { AtlasShell } from "@/components/layout/atlas-shell";
import { BackendStatus, type BackendState } from "@/components/system/backend-status";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { getDashboardState } from "@/lib/api/dashboard";
import { getCandles } from "@/lib/api/market";
import { getMarketBriefing, type Headline } from "@/lib/api/briefing";
import { atlasFetch, AtlasApiError } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
import { mapDashboardState } from "@/lib/api/mappers";
import type { Candle, DashboardViewModel } from "@/lib/api/types";
const unavailable = mapDashboardState({ status: "OFFLINE" });
export function AtlasAppShell({ refreshMs = 30000, timeoutMs = 12000 }: { refreshMs?: number; timeoutMs?: number } = {}) {
  const [state, setState] = useState<DashboardViewModel>(unavailable);
  const [backend, setBackend] = useState<BackendState>("checking");
  const [sessionRequired, setSessionRequired] = useState(false);
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
        setState(unavailable); setSessionRequired(true); setBackend(healthy ? "online" : "offline");
        return;
      }
      setSessionRequired(false);
      if (dashboard.status === "fulfilled" && healthy && dashboard.value.connection === "connected" && dashboard.value.account.id) {
        setState(dashboard.value); setBackend("online");
      } else {
        setState(unavailable); setBackend(healthy ? "degraded" : "offline");
      }
    }
    void refresh();
    const interval = setInterval(() => { void refresh(); }, refreshMs);
    return () => { active = false; clearInterval(interval); controllers.forEach((controller) => controller.abort()); };
  }, [refreshMs, timeoutMs]);
  useEffect(() => {
    let active = true;
    getMarketBriefing().then((items) => { if (active) { setHeadlines(items); setBriefingAvailable(true); } })
      .catch(() => { if (active) { setHeadlines([]); setBriefingAvailable(false); } });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    async function refreshChart() {
      try {
        const series = await getCandles(symbol, timeframe);
        if (active) { setCandles(series); setChartStatus(series.length ? "" : "Market data unavailable"); }
      } catch { if (active) { setCandles([]); setChartStatus("Market data unavailable"); } }
    }
    setCandles([]); setChartStatus("Loading market data…");
    void refreshChart();
    const interval = setInterval(() => { void refreshChart(); }, 60000);
    return () => { active = false; clearInterval(interval); };
  }, [symbol, timeframe]);
  return <AtlasShell><section data-testid="atlas-app-shell">
    {sessionRequired ? <main className="atlas-auth-required atlas-card">
      <h1>Sign in to view your ATLAS dashboard</h1>
      <p>Your account data stays private until you sign in.</p>
      <a className="atlas-primary-button" href="/login">Go to sign in</a>
    </main> : <>
    <BackendStatus status={backend} />
    {chartStatus && <span role="status" className="atlas-chart-status">{chartStatus}</span>}
    <DashboardScreen state={state} candles={candles} symbol={symbol} timeframe={timeframe}
      signals={state.signals ?? []} activity={state.activity ?? []} headlines={headlines} briefingAvailable={briefingAvailable}
      onMarketChange={(nextSymbol, nextTimeframe) => { setSymbol(nextSymbol); setTimeframe(nextTimeframe); }} />
    </>}
  </section></AtlasShell>;
}
