import { SectorHeader } from "@/components/system/sector-header";

export type SignalView = { symbol: string; direction: string; confidence?: number | null; rationale?: string | null; riskWarning?: string | null; timestamp?: string | null };
export function SignalsPanel({ signals, available = true }: { signals: SignalView[]; available?: boolean }) {
  return <section className="atlas-card atlas-signals atlas-feature-3d atlas-mobile-reference-card" id="signals">
    <SectorHeader title="Signals" kind="signals" />
    {!available ? <div className="atlas-empty-line atlas-mobile-reference-empty">Signals unavailable</div> : signals.length === 0 ? <div className="atlas-empty-line atlas-mobile-reference-empty">No active signals</div> :
      <div className="atlas-signal-list">{signals.map((s, i) => <article key={`${s.symbol}-${i}`}>
        <div><strong>{s.symbol}</strong><span>{s.direction}</span></div>
        {s.confidence != null && <small>{s.confidence}% confidence</small>}
        {s.timestamp && <time dateTime={s.timestamp}>{s.timestamp}</time>}
        {s.rationale && <p>{s.rationale}</p>}{s.riskWarning && <em>{s.riskWarning}</em>}
      </article>)}</div>}
  </section>;
}
