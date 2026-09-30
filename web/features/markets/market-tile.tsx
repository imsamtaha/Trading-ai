export function MarketTile({ symbol, price, changePct }: { symbol: string; price: number | null; changePct: number | null }) {
  const positive = (changePct ?? 0) >= 0;
  return (
    <article className="atlas-card atlas-market-tile">
      <span className="atlas-card-label">{symbol}</span>
      <strong>{price == null ? "—" : price.toLocaleString("en-US", { maximumFractionDigits: 5 })}</strong>
      <small className={positive ? "is-positive" : "is-negative"}>{changePct == null ? "—" : `${positive ? "+" : ""}${changePct.toFixed(2)}%`}</small>
      <span className="atlas-sparkline" aria-hidden="true">╱╲╱╱╲╱</span>
    </article>
  );
}
