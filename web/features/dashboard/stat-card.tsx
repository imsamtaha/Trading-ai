export function StatCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "positive" | "warning" }) {
  return (
    <article className={`atlas-card atlas-stat atlas-stat--${tone}`}>
      <span className="atlas-card-label">{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
