"use client";
import { useState } from "react";
import Image from "next/image";
import type { Candle, DashboardViewModel } from "@/lib/api/types";
import { MarketTile } from "@/features/markets/market-tile";
import { MarketWorkspace } from "@/features/markets/market-workspace";
import { RiskPanel } from "@/features/risk/risk-panel";
import { ActivityPanel, type ActivityEvent } from "@/features/activity/activity-panel";
import { PositionsPanel } from "@/features/trades/positions-panel";
import { SignalsPanel, type SignalView } from "@/features/signals/signals-panel";
import { AtlasAssistant } from "@/features/ai/atlas-assistant";
import { sendAgentMessage } from "@/lib/api/agent";
import type { Headline } from "@/lib/api/briefing";
import { AgentBadge } from "@/components/system/agent-badge";
import { TrainingPanel } from "@/features/training/training-panel";
import { ExecutionAgentPanel } from "@/features/execution/execution-agent-panel";

type Language = "ar" | "en";
const money = (v: number | null) => v == null ? "PRIVATE" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MiniCard = ({ label, value, tone = "gold" }: { label: string; value: string; tone?: "gold" | "green" }) => (
  <article className={`atlas-mini-card atlas-mini-card--${tone}`}><span>{label}</span><strong>{value}</strong></article>
);

export function DashboardScreen({ state, candles = [], symbol = "XAUUSD", timeframe = "1h", signals = [], activity = [], headlines = [], briefingAvailable = false, positionsAvailable, signalsAvailable, activityAvailable, assistantAvailable = true, assistantLockedHref = "/login?returnTo=%2Fdashboard", intelligenceAvailable = true, language = "ar", onMarketChange }: {
  state: DashboardViewModel; candles?: Candle[]; symbol?: string; timeframe?: string; signals?: SignalView[]; activity?: ActivityEvent[]; headlines?: Headline[]; briefingAvailable?: boolean;
  positionsAvailable?: boolean; signalsAvailable?: boolean; activityAvailable?: boolean; assistantAvailable?: boolean; assistantLockedHref?: string; intelligenceAvailable?: boolean; language?: Language; onMarketChange?: (symbol: string, timeframe: string) => void;
}) {
  const ar = language === "ar";
  const [activeNav, setActiveNav] = useState("markets");
  const connected = state.connection === "connected";
  const chartPosition = connected ? state.positions.find((p) => p.symbol === symbol) : undefined;
  const chartSignal = connected ? signals.find((s) => s.symbol === symbol) : undefined;
  const signal = chartSignal?.direction ?? "OBSERVE";
  const confidence = chartSignal?.confidence == null ? "?" : `${chartSignal.confidence}%`;

  return <div className="atlas-dashboard atlas-dashboard--mockup" id="dashboard" dir={ar ? "rtl" : "ltr"}>
    <header className="atlas-mock-topbar" data-testid="atlas-dashboard-topbar">
      <div className="atlas-mock-brand">
        <Image src="/atlas-logo.webp" alt="ATLAS" width={84} height={84} unoptimized />
        <div>
          <h1>ATLAS</h1>
        </div>
      </div>
      <div className="atlas-mock-status">
        <span className="atlas-mode-pill">PAPER MODE</span>
        <span>{state.userRole === "OWNER" ? "OWNER" : (ar ? "خاص" : "Private")}</span>
        <span className={connected ? "is-connected" : ""}>{connected ? (ar ? "بيانات MT5 متصلة" : "MT5 data connected") : (ar ? "MT5 غير متصل" : "MT5 disconnected")}</span>
        {state.connection === "offline" && <span className="sr-only">Backend offline</span>}
      </div>
    </header>

    <section className="atlas-command-strip" aria-label={ar ? "حالة مساحة العمل" : "Workspace mode"}>
      <span><strong>{ar ? "المحاكاة" : "Simulation"}</strong>{ar ? " تداول ورقي فقط" : " Paper only"}</span>
      <span><strong>{ar ? "المخاطر" : "Risk"}</strong>{ar ? " قبل القرار" : " before action"}</span>
      <span><strong>{ar ? "المجلس" : "Council"}</strong>{ar ? " تحليل متعدد الوكلاء" : " multi-agent analysis"}</span>
    </section>

    {intelligenceAvailable && <section className="atlas-insight-grid" data-testid="atlas-insight-grid">
      <MiniCard label={ar ? "الاتجاه" : "Trend"} value={signal === "BUY" ? (ar ? "صاعد" : "BULLISH") : signal === "SELL" ? (ar ? "هابط" : "BEARISH") : (ar ? "محايد" : "NEUTRAL")} />
      <MiniCard label={ar ? "الإشارة" : "Signal"} value={signal} />
      <MiniCard label={ar ? "التحيز" : "Bias"} value={signal === "OBSERVE" ? "?" : signal} />
      <MiniCard label={ar ? "الثقة" : "Confidence"} value={confidence} />
    </section>}

    <div className="atlas-chart-stage">
      <MarketWorkspace
        candles={candles}
        symbol={symbol}
        timeframe={timeframe}
        onChange={onMarketChange}
        signal={chartSignal}
        levels={{ entry: chartPosition?.entry, stopLoss: chartPosition?.stopLoss, takeProfit: chartPosition?.takeProfit }}
        language={language}
      />
    </div>

    <section className="atlas-stat-strip" data-testid="atlas-stat-strip">
      <MiniCard label={ar ? "الرصيد" : "Balance"} value={money(state.account.balance)} />
      <MiniCard label={ar ? "القيمة" : "Equity"} value={money(state.account.equity)} />
      <MiniCard label="P/L" value={money(state.account.floatingPnl)} tone={(state.account.floatingPnl ?? 0) >= 0 ? "green" : "gold"} />
      <MiniCard label={ar ? "المراكز" : "Positions"} value={String(state.positions.length)} />
      <MiniCard label={ar ? "المحرك" : "Engine"} value="PAPER" />
    </section>

    <div className="atlas-ai-featured" id="ai"><AtlasAssistant sendMessage={sendAgentMessage} language={language} enabled={assistantAvailable} lockedHref={assistantLockedHref} /></div>

    <nav className="atlas-bottom-actions atlas-bottom-actions--five" aria-label={ar ? "التنقل الرئيسي" : "Dashboard actions"}>
      <a href="#markets" aria-label={ar ? "الأسواق" : "Markets"} aria-current={activeNav === "markets" ? "page" : undefined} onClick={() => setActiveNav("markets")}>{ar ? "الأسواق" : "Markets"}</a>
      <a href="#signals" aria-label={ar ? "الإشارات" : "Signals"} aria-current={activeNav === "signals" ? "page" : undefined} onClick={() => setActiveNav("signals")}>{ar ? "الإشارات" : "Signals"}</a>
      <a href="#risk" aria-label={ar ? "المخاطر" : "Risk"} aria-current={activeNav === "risk" ? "page" : undefined} onClick={() => setActiveNav("risk")}>{ar ? "المخاطر" : "Risk"}</a>
      <a href="#news" aria-label={ar ? "الأخبار" : "News"} aria-current={activeNav === "news" ? "page" : undefined} onClick={() => setActiveNav("news")}>{ar ? "الأخبار" : "News"}</a>
      <a href="#ai" aria-label="ATLAS AI" aria-current={activeNav === "ai" ? "page" : undefined} onClick={() => setActiveNav("ai")}>ATLAS AI</a>
    </nav>

    <section className="atlas-market-strip atlas-secondary-zone" id="markets">{state.markets.map((market) => <MarketTile key={market.symbol} {...market} />)}</section>
    <section className="atlas-workspace-grid atlas-workspace-grid--two atlas-secondary-zone">
      <PositionsPanel positions={state.positions} available={positionsAvailable ?? connected} language={language} />
      <SignalsPanel signals={signals} available={signalsAvailable ?? connected} language={language} />
    </section>
    <section className="atlas-lower-grid atlas-secondary-zone">
      <div><RiskPanel risk={state.risk} language={language} /></div>
      <ActivityPanel events={activity} available={activityAvailable ?? connected} language={language} />
    </section>

    <ExecutionAgentPanel language={language} />
    {state.userRole === "OWNER" && <TrainingPanel language={language} />}

    <section className="atlas-lower-grid atlas-secondary-zone">
      <div className="atlas-card atlas-activity-card" id="analytics">
        <h2 className="atlas-agent-title" dir={ar ? "rtl" : "ltr"}>{ar ? <><span>الأداء</span><AgentBadge /></> : <><AgentBadge /><span>Performance</span></>}</h2>
        <p className="atlas-empty-line">{ar ? "التحليلات الموثقة غير متاحة" : "Verified analytics unavailable"}</p>
      </div>
      <div className="atlas-card atlas-activity-card atlas-feature-3d" id="news">
        <h2 className="atlas-agent-title" dir={ar ? "rtl" : "ltr"}>{ar ? <><span>أخبار السوق</span><AgentBadge /></> : <><AgentBadge /><span>Market News</span></>}</h2>
        {!briefingAvailable ? <p className="atlas-empty-line">{ar ? "الأخبار غير متاحة حالياً" : "Market news unavailable"}</p>
          : headlines.length === 0 ? <p className="atlas-empty-line">{ar ? "لا توجد أخبار حديثة" : "No recent headlines"}</p>
          : <ul className="atlas-activity-list atlas-news-list">{headlines.slice(0, 3).map((item, i) => <li key={i}>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a> : item.title}{item.source && <small className="atlas-news-source">{ar ? "المصدر: " : "Source: "}{item.source}</small>}</li>)}</ul>}
      </div>
    </section>
  </div>;
}
