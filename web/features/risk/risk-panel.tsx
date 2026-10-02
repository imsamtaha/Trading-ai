import type { RiskViewModel } from "@/lib/api/types";
import { SectorHeader } from "@/components/system/sector-header";

const pct = (v: number | null) => v == null ? "—" : `${v}%`;
const rows = [
  ["Overall Risk", "overall"], ["Daily Loss", "dailyLoss"], ["Drawdown", "drawdown"],
  ["Exposure", "exposure"], ["Position Size", "positionSize"], ["Open Risk", "aggregateOpenRisk"],
] as const;

export function RiskPanel({ risk, language = "en" }: { risk: RiskViewModel; language?: "ar" | "en" }) {
  return <section className="atlas-card atlas-risk-panel atlas-feature-3d atlas-mobile-reference-card" id="risk">
    <SectorHeader title="Risk Controls" titleAr="ضوابط المخاطر" kind="risk" language={language} />
    <div className="atlas-risk-list">
      {rows.map(([label, key]) => <div className="atlas-risk-row" key={key}><span>{label}</span><div className="atlas-risk-track"><i style={{ width: `${Math.max(0, Math.min(100, risk[key] ?? 0))}%` }} /></div><strong>{pct(risk[key])}</strong></div>)}
    </div>
    {risk.warnings.length > 0 && <div className="atlas-warning">{risk.warnings.join(" · ")}</div>}
  </section>;
}
