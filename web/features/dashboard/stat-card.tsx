import type { ReactElement } from "react";
export function StatCard({ label, value, detail }: { label: string; value: string; detail?: string | null }): ReactElement {
  return <article className="atlas-card atlas-stat-card"><p className="atlas-card__label">{label}</p><strong className="atlas-stat-card__value">{value}</strong>{detail && <p className="atlas-card__detail">{detail}</p>}</article>;
}
