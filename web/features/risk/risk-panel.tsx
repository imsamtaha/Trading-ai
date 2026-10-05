import type { ReactElement } from "react";
import type { RiskViewModel } from "../../lib/api/types";
export function RiskPanel({ risk }: { risk: RiskViewModel | null }): ReactElement {
  if (!risk) return <section className="atlas-card"><div className="atlas-section-heading"><h2>Risk protection</h2><span className="atlas-pill atlas-pill--muted">UNAVAILABLE</span></div><p className="atlas-empty">Risk telemetry unavailable from backend.</p></section>;
  const rows = [["Daily loss used", risk.dailyLossUsage], ["Drawdown", risk.drawdown], ["Exposure", risk.exposure], ["Position size utilization", risk.positionSizeUtilization], ["Aggregate open risk", risk.aggregateOpenRisk]] as const;
  return <section className="atlas-card"><div className="atlas-section-heading"><h2>Risk protection</h2><span className="atlas-pill">{risk.level ?? "—"}</span></div><div className="atlas-risk-grid">{rows.map(([label, value]) => <div className="atlas-risk-row" key={label}><span>{label}</span><strong>{value === null ? "—" : `${value}%`}</strong></div>)}</div><p className="atlas-card__detail">Protection: {risk.protection ?? "—"}</p>{risk.warnings.length > 0 && <ul className="atlas-warnings">{risk.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul>}</section>;
}
