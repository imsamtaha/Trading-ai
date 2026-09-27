import type { DashboardViewModel } from "@/lib/api/types";
import { AccountCard } from "./account-card";
import { StatCard } from "./stat-card";
import { MarketTile } from "@/features/markets/market-tile";
import { RiskPanel } from "@/features/risk/risk-panel";
import { ActivityPanel } from "@/features/activity/activity-panel";

const money = (v: number | null) => v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function DashboardScreen({ state }: { state: DashboardViewModel }) {
  return (
    <div className="atlas-dashboard" id="dashboard">
      <header className="atlas-dashboard-header"><div><span className="eyebrow">JUST AI / ATLAS</span><h1>Trading Intelligence</h1></div><div className="atlas-live-pill">{state.connection === "connected" ? "Live data" : "Data unavailable"}</div></header>
      <section className="atlas-account-grid"><AccountCard account={state.account} connection={state.connection} /><StatCard label="Equity" value={money(state.account.equity)} /><StatCard label="Floating P/L" value={money(state.account.floatingPnl)} tone={(state.account.floatingPnl ?? 0) >= 0 ? "positive" : "warning"} /><StatCard label="Daily P/L" value={money(state.account.dailyPnl)} tone={(state.account.dailyPnl ?? 0) >= 0 ? "positive" : "warning"} /></section>
      <section className="atlas-market-strip" id="markets">{state.markets.map((market) => <MarketTile key={market.symbol} {...market} />)}</section>
      <section className="atlas-chart-placeholder" id="trade"><div><span className="atlas-card-label">Primary workspace</span><h2>Market chart</h2></div><div className="atlas-chart-grid"><span>Chart workspace loading in next module</span></div></section>
      <section className="atlas-lower-grid"><RiskPanel risk={state.risk} /><ActivityPanel /></section>
    </div>
  );
}
