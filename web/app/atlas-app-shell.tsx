"use client";
import { useEffect, useState } from "react";
import { AtlasShell } from "@/components/layout/atlas-shell";
import { BackendStatus, type BackendState } from "@/components/system/backend-status";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { getDashboardState } from "@/lib/api/dashboard";
import { getCandles } from "@/lib/api/market";
import { getMarketBriefing, type Headline } from "@/lib/api/briefing";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
import { mapDashboardState } from "@/lib/api/mappers";
import type { Candle, DashboardViewModel } from "@/lib/api/types";
const unavailable = mapDashboardState({ status: "OFFLINE" });
export function AtlasAppShell() {
  const [state, setState] = useState<DashboardViewModel>(unavailable);
  const [backend, setBackend] = useState<BackendState>("checking");
  const [symbol, setSymbol] = useState("XAUUSD");
  const [timeframe, setTimeframe] = useState("1h");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [briefingAvailable, setBriefingAvailable] = useState(false);
  const [chartStatus, setChartStatus] = useState("Loading market data…");
  useEffect(() => {
    let active = true;
    Promise.allSettled([atlasFetch(apiPath("/health"), { cache: "no-store" }), getDashboardState()]).then(([health, dashboard]) => {
      if (!active) return;
      if (dashboard.status === "fulfilled" && health.status === "fulfilled" && dashboard.value.connection === "connected" && dashboard.value.account.id) {
        setState(dashboard.value); setBackend("online");
      } else {
        setState(unavailable); setBackend(health.status === "fulfilled" ? "degraded" : "offline");
      }
    });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    getMarketBriefing().then((items) => { if (active) { setHeadlines(items); setBriefingAvailable(true); } })
      .catch(() => { if (active) { setHeadlines([]); setBriefingAvailable(false); } });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    setCandles([]); setChartStatus("Loading market data…");
    getCandles(symbol, timeframe).then((series) => {
      if (!active) return;
      setCandles(series); setChartStatus(series.length ? "" : "Market data unavailable");
    }).catch(() => { if (active) { setCandles([]); setChartStatus("Market data unavailable"); } });
    return () => { active = false; };
  }, [symbol, timeframe]);
  return <AtlasShell><section data-testid="atlas-app-shell">
    <BackendStatus status={backend} />
    {chartStatus && <span role="status" className="atlas-chart-status">{chartStatus}</span>}
    <DashboardScreen state={state} candles={candles} symbol={symbol} timeframe={timeframe}
      signals={state.signals ?? []} activity={state.activity ?? []} headlines={headlines} briefingAvailable={briefingAvailable}
      onMarketChange={(nextSymbol, nextTimeframe) => { setSymbol(nextSymbol); setTimeframe(nextTimeframe); }} />
  </section></AtlasShell>;
}
