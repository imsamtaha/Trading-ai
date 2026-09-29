import type { Position } from "@/lib/api/types";
import { AgentBadge } from "@/components/system/agent-badge";
const show = (v: number | null | undefined) => v == null ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: 5 });
export function PositionsPanel({ positions, available }: { positions: Position[]; available: boolean }) {
  return (
    <section className="atlas-card atlas-positions" id="positions">
      <div className="atlas-section-heading"><div><span className="atlas-card-label">Execution state</span><h2>Open Positions <AgentBadge /></h2></div><strong>{available ? positions.length : "—"}</strong></div>
      {!available ? <div className="atlas-empty-line">Positions unavailable</div> : positions.length === 0 ? <div className="atlas-empty-line">No open positions</div> : (
        <div className="atlas-position-list">{positions.map((p, i) => <div className="atlas-position-row" key={`${p.symbol}-${i}`}>
          <div><strong>{p.symbol}</strong><span>{p.direction ?? "—"}</span></div>
          <div><small>Size</small><span>{show(p.size)}</span></div><div><small>Entry</small><span>{show(p.entry)}</span></div>
          <div><small>Current</small><span>{show(p.current)}</span></div><div><small>P/L</small><span className={p.pnl == null ? "" : p.pnl >= 0 ? "is-positive" : "is-negative"}>{show(p.pnl)}</span></div>
          <div><small>SL / TP</small><span>{show(p.stopLoss)} / {show(p.takeProfit)}</span></div><div><small>Status</small><span>{p.status ?? "—"}</span></div>
        </div>)}</div>
      )}
    </section>
  );
}



