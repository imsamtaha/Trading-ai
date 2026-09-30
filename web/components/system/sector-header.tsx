import { AgentBadge } from "@/components/system/agent-badge";

type SectorKind = "positions" | "signals" | "risk" | "activity";

function SectorIcon({ kind }: { kind: SectorKind }) {
  if (kind === "positions") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V10M10 20V4M15 20v-7M20 20V7" /></svg>;
  if (kind === "signals") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17l5-6 4 4 7-9 2 2" /><circle cx="3" cy="17" r="1" /><circle cx="8" cy="11" r="1" /><circle cx="12" cy="15" r="1" /><circle cx="19" cy="6" r="1" /></svg>;
  if (kind === "risk") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.7-2.7 8-7 10-4.3-2-7-5.3-7-10V6l7-3z" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>;
}

export function SectorHeader({ title, kind }: { title: string; kind: SectorKind }) {
  return <div className="atlas-reference-header">
    <span className={`atlas-sector-icon atlas-sector-icon--${kind}`}><SectorIcon kind={kind} /></span>
    <div className="atlas-reference-title"><AgentBadge /><h2>{title}</h2></div>
    <span className="atlas-sector-chevron" aria-hidden="true">›</span>
  </div>;
}
