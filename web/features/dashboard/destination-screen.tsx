"use client";
import { useEffect, useState, type ReactElement } from "react";
import type { Destination } from "../../lib/navigation";
import { AtlasAppShell } from "../../components/layout/atlas-shell";
import { getDashboardState } from "../../lib/api/dashboard";
import { mapDashboardState } from "../../lib/api/mappers";
import type { DashboardViewModel } from "../../lib/api/types";
import { AccountCard } from "./account-card";
import { RiskPanel } from "../risk/risk-panel";
import { PositionsPanel } from "../trades/positions-panel";
import { SignalsPanel } from "../signals/signals-panel";
import { AtlasAssistant } from "../ai/atlas-assistant";
const TITLES: Record<Destination, string> = { dashboard: "Trading Intelligence", markets: "Markets", trade: "Trade", signals: "Signals", risk: "Risk", analytics: "Analytics", news: "News", ai: "ATLAS AI", account: "Account" };
export function DestinationScreen({ active }: { active: Destination }): ReactElement {
  const [state, setState] = useState<DashboardViewModel>(() => mapDashboardState({ status: "OFFLINE" }));
  useEffect(() => { let live = true; getDashboardState().then(data => { if (live) setState(data); }).catch(() => { if (live) setState(mapDashboardState({ status: "OFFLINE" })); }); return () => { live = false; }; }, []);
  let body: ReactElement;
  if (active === "trade") body = <PositionsPanel positions={state.connection === "online" ? state.positions : null} unavailable={state.connection !== "online"} />;
  else if (active === "signals") body = <SignalsPanel signals={state.signals} />;
  else if (active === "risk") body = <RiskPanel risk={state.risk} />;
  else if (active === "ai") body = <AtlasAssistant />;
  else if (active === "account") body = <section className="atlas-account-section"><div className="atlas-section-heading"><h2>Broker account</h2><span className="atlas-pill">{state.mode ?? "—"}</span></div><AccountCard account={state.account} /></section>;
  else body = <section className="atlas-card"><h2>{active === "news" ? "Market news" : "Performance analytics"}</h2><p className="atlas-empty">This data is not currently provided by the connected ATLAS API.</p></section>;
  return <AtlasAppShell active={active}><div className="atlas-dashboard"><section className="atlas-page-heading"><div><p className="atlas-eyebrow">ATLAS WORKSPACE</p><h1>{TITLES[active]}</h1></div><span className={`atlas-connection atlas-connection--${state.connection}`}><i />{state.connection.toUpperCase()}</span></section>{state.connection !== "online" && <div role="status" className="atlas-offline-banner">{state.connection === "offline" ? "Backend is offline. Live data is unavailable." : "Backend connection state is unknown."}</div>}{body}</div></AtlasAppShell>;
}
