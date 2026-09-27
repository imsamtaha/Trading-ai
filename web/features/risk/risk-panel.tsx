import type { RiskViewModel } from "@/lib/api/types";

const pct = (v: number | null) => v == null ? "—" : `${v}%`;
const rows = [
  ["Overall Risk", "overall"], ["Daily Loss", "dailyLoss"], ["Drawdown", "drawdown"],
  ["Exposure", "exposure"], ["Position Size", "positionSize"], ["Open Risk", "aggregateOpenRisk"],
] as const;

export function RiskPanel({ risk }: { risk: RiskViewModel }) {
  return (
    <section className="atlas-card atlas-risk-panel" id="risk">
      <div className="atlas-section-heading"><div><span className="atlas-card-label">Capital protection</span><h2>Risk Controls</h2></div><strong>{risk.protectionState ?? "Unknown"}</strong></div>
      <div className="atlas-risk-list">
        {rows.map(([label, key]) => <div className="atlas-risk-row" key={key}><span>{label}</span><div className="atlas-risk-track"><i style={{ width: `${Math.max(0, Math.min(100, risk[key] ?? 0))}%` }} /></div><strong>{pct(risk[key])}</strong></div>)}
      </div>
      {risk.warnings.length > 0 && <div className="atlas-warning">{risk.warnings.join(" · ")}</div>}
    </section>
  );
}
