import type { ReactElement } from "react";
export interface SignalItem { symbol: string; type: string; message: string }
export function SignalsPanel({ signals }: { signals: SignalItem[] }): ReactElement {
  return <section className="atlas-card"><div className="atlas-section-heading"><h2>Signals & activity</h2><span className="atlas-pill atlas-pill--muted">{signals.length}</span></div>{signals.length ? <div className="atlas-position-list">{signals.map((signal, i) => <article className="atlas-signal-row" key={`${signal.symbol}-${i}`}><strong>{signal.symbol}</strong><span>{signal.type}</span><p>{signal.message}</p></article>)}</div> : <p className="atlas-empty">No signal activity reported.</p>}</section>;
}
