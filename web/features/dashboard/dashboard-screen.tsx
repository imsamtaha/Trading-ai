import type { DashboardViewModel } from "@/lib/api/types";
import type { Candle } from "@/lib/api/types";
import { AccountCard } from "./account-card";
import { StatCard } from "./stat-card";
import { MarketTile } from "@/features/markets/market-tile";
import { MarketWorkspace } from "@/features/markets/market-workspace";
import { RiskPanel } from "@/features/risk/risk-panel";
import { ActivityPanel, type ActivityEvent } from "@/features/activity/activity-panel";
import { PositionsPanel } from "@/features/trades/positions-panel";
import { SignalsPanel, type SignalView } from "@/features/signals/signals-panel";
import { AtlasAssistant } from "@/features/ai/atlas-assistant";
import { sendAgentMessage } from "@/lib/api/agent";
import type { Headline } from "@/lib/api/briefing";
const money = (v: number | null) => v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export function DashboardScreen({ state, candles = [], symbol = "XAUUSD", timeframe = "1h", signals = [], activity = [], headlines = [], briefingAvailable = false, positionsAvailable, signalsAvailable, activityAvailable, onMarketChange }: {
  state: DashboardViewModel; candles?: Candle[]; symbol?: string; timeframe?: string; signals?: SignalView[]; activity?: ActivityEvent[]; headlines?: Headline[]; briefingAvailable?: boolean;
  positionsAvailable?: boolean; signalsAvailable?: boolean; activityAvailable?: boolean; onMarketChange?: (symbol: string, timeframe: string) => void;
}) {
  const connected = state.connection === "connected";
  return <div className="atlas-dashboard" id="dashboard">
    <header className="atlas-dashboard-header"><div><span className="eyebrow">ATLAS INTELLIGENCE</span><h1>Trading Intelligence</h1></div><div className="atlas-live-pill">{connected ? "Live data" : "Data unavailable"}</div></header>
    <section className="atlas-account-grid"><AccountCard account={state.account} connection={state.connection} /><StatCard label="Equity" value={money(state.account.equity)} /><StatCard label="Floating P/L" value={money(state.account.floatingPnl)} tone={(state.account.floatingPnl ?? 0) >= 0 ? "positive" : "warning"} /><StatCard label="Daily P/L" value={money(state.account.dailyPnl)} tone={(state.account.dailyPnl ?? 0) >= 0 ? "positive" : "warning"} /></section>
    <section className="atlas-market-strip" id="markets">{state.markets.map((market) => <MarketTile key={market.symbol} {...market} />)}</section>
    <MarketWorkspace candles={candles} symbol={symbol} timeframe={timeframe} onChange={onMarketChange} />
    <section className="atlas-workspace-grid"><PositionsPanel positions={state.positions} available={positionsAvailable ?? connected} /><SignalsPanel signals={signals} available={signalsAvailable ?? connected} /><AtlasAssistant sendMessage={sendAgentMessage} /></section>
    <section className="atlas-lower-grid"><RiskPanel risk={state.risk} /><ActivityPanel events={activity} available={activityAvailable ?? connected} /></section>
    <section className="atlas-lower-grid"><div className="atlas-card atlas-activity-card" id="analytics"><span className="atlas-card-label">Analytics</span><h2>Performance</h2><p className="atlas-empty-line">Verified analytics unavailable</p></div><div className="atlas-card atlas-activity-card" id="news"><span className="atlas-card-label">News</span><h2>Market briefing</h2>{!briefingAvailable ? <p className="atlas-empty-line">Market briefing unavailable</p> : headlines.length === 0 ? <p className="atlas-empty-line">No recent headlines</p> : <ul className="atlas-activity-list">{headlines.map((item, i) => <li key={i}>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a> : item.title}</li>)}</ul>}</div></section>
  </div>;
}
