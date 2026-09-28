import type { ReactElement } from "react";
import type { Position } from "../../lib/api/types";
export function ActivityPanel({ positions }: { positions: Position[] }): ReactElement {
  return <section className="atlas-card"><div className="atlas-section-heading"><h2>Open positions</h2><span className="atlas-pill atlas-pill--muted">{positions.length}</span></div>{positions.length ? <div className="atlas-position-list">{positions.map((p, i) => <div className="atlas-position-row" key={`${p.symbol}-${i}`}><strong>{p.symbol}</strong><span>{p.direction ?? "—"}</span><span>{p.volume ?? "—"}</span><strong>{p.profit === null ? "—" : p.profit.toLocaleString("en-US", { style: "currency", currency: "USD" })}</strong></div>)}</div> : <p className="atlas-empty">No open positions reported.</p>}</section>;
}
