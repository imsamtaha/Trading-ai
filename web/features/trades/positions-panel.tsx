import type { Position } from "@/lib/api/types";
import { SectorHeader } from "@/components/system/sector-header";

const show = (v: number | null | undefined) => v == null ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: 5 });

export function PositionsPanel({ positions, available }: { positions: Position[]; available: boolean }) {
  return <section className="atlas-card atlas-positions atlas-feature-3d atlas-mobile-reference-card" id="positions">
    <SectorHeader title="Open Positions" kind="positions" />
    {!available ? <div className="atlas-empty-line atlas-mobile-reference-empty">Positions unavailable</div> : positions.length === 0 ? <div className="atlas-empty-line atlas-mobile-reference-empty">No open positions</div> :
      <div className="atlas-position-list">{positions.map((p, i) => <div className="atlas-position-row" key={`${p.symbol}-${i}`}>
        <div><strong>{p.symbol}</strong><span>{p.direction ?? "—"}</span></div>
        <div><small>Size</small><span>{show(p.size)}</span></div><div><small>Entry</small><span>{show(p.entry)}</span></div>
        <div><small>Current</small><span>{show(p.current)}</span></div><div><small>P/L</small><span className={p.pnl == null ? "" : p.pnl >= 0 ? "is-positive" : "is-negative"}>{show(p.pnl)}</span></div>
        <div><small>SL / TP</small><span>{show(p.stopLoss)} / {show(p.takeProfit)}</span></div><div><small>Status</small><span>{p.status ?? "—"}</span></div>
      </div>)}</div>}
  </section>;
}
