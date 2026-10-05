import type { ReactElement } from "react";
import type { DashboardViewModel } from "../../lib/api/types";
import { AccountCard } from "./account-card";
import { StatCard } from "./stat-card";
import { MarketTile } from "../markets/market-tile";
import { RiskPanel } from "../risk/risk-panel";
import { ActivityPanel } from "../activity/activity-panel";
import { PositionsPanel } from "../trades/positions-panel";
import { SignalsPanel } from "../signals/signals-panel";
import { AtlasAssistant } from "../ai/atlas-assistant";
export function DashboardScreen({ state }: { state: DashboardViewModel }): ReactElement {
  return <div className="atlas-dashboard"><section className="atlas-page-heading"><div><p className="atlas-eyebrow">ATLAS WORKSPACE</p><h1>Trading Intelligence</h1><p className="atlas-heading-copy">Account, market and protection status at a glance.</p></div><span className={`atlas-connection atlas-connection--${state.connection}`}><i />{state.connection.toUpperCase()}</span></section>
    {state.connection === "offline" && <div role="status" className="atlas-offline-banner">Backend is offline. Live account and risk telemetry are unavailable.</div>}
    {state.connection === "unknown" && <div role="status" className="atlas-offline-banner">Backend connection state is unknown.</div>}
    <section className="atlas-account-section"><div className="atlas-section-heading"><div><p className="atlas-eyebrow">ACCOUNT OVERVIEW</p><h2>Broker account</h2></div><span className="atlas-pill">{state.mode ?? "—"}</span></div><AccountCard account={state.account} /></section>
    <div className="atlas-dashboard-grid"><RiskPanel risk={state.risk} /><ActivityPanel positions={state.positions} /></div>
    <div className="atlas-dashboard-grid"><PositionsPanel positions={state.connection === "offline" ? null : state.positions} unavailable={state.connection !== "online"} /><SignalsPanel signals={state.signals} /></div>
    <AtlasAssistant />
    <section className="atlas-card atlas-markets-card"><div className="atlas-section-heading"><div><p className="atlas-eyebrow">LIVE SNAPSHOT</p><h2>Markets</h2></div></div>{state.markets.length ? <div className="atlas-markets-list">{state.markets.map((market, i) => <MarketTile key={`${market.label}-${i}`} market={market} />)}</div> : <p className="atlas-empty">Market data is currently unavailable.</p>}</section>
  </div>;
}
