import type { ReactElement } from "react";
import type { MarketTile as MarketTileModel } from "../../lib/api/types";
export function MarketTile({ market }: { market: MarketTileModel }): ReactElement {
  const change = market.changePercent;
  return <article className="atlas-market-tile"><div><strong>{market.label}</strong><span>{market.category ?? "Market"}</span></div><strong>{market.price === null ? "—" : market.price.toLocaleString("en-US", { maximumFractionDigits: 5 })}</strong><span className={change === null ? "" : change >= 0 ? "atlas-positive" : "atlas-negative"}>{change === null ? "—" : `${change > 0 ? "+" : ""}${change.toFixed(2)}%`}</span><span className="atlas-market-state">{market.marketState ?? "—"}</span></article>;
}
