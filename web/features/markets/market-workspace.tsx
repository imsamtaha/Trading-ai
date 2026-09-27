"use client";

import { useCallback, useState } from "react";
import type { Candle } from "@/lib/api/types";
import type { SignalView } from "@/features/signals/signals-panel";
import { ChartToolbar } from "@/features/chart/chart-toolbar";
import { TradingChart } from "@/features/chart/trading-chart";
import { formatOhlc, toPriceLines, type TradeLevels } from "@/features/chart/chart-overlays";
export function MarketWorkspace({ candles, symbol, timeframe, levels = {}, signal, onChange }: {
  candles: Candle[]; symbol: string; timeframe: string; levels?: TradeLevels; signal?: SignalView; onChange?: (symbol: string, timeframe: string) => void;
}) {
  const [hovered, setHovered] = useState<Candle | null>(null);
  const onOhlcChange = useCallback((candle: Candle | null) => setHovered(candle), []);
  const priceLines = toPriceLines(levels);
  const latest = candles.length ? candles[candles.length - 1] : null;
  return <section className="atlas-card atlas-market-workspace" id="trade">
    <ChartToolbar symbol={symbol} timeframe={timeframe} onChange={onChange} />
    {signal && <div className="atlas-chart-context" role="status">{signal.direction} signal{signal.confidence != null && ` · ${signal.confidence}% confidence`}</div>}
    {priceLines.length > 0 && <div className="atlas-chart-levels">{priceLines.map((line) => <span key={line.title}>{line.title} {line.price.toLocaleString("en-US", { maximumFractionDigits: 5 })}</span>)}</div>}
    {latest && <div className="atlas-chart-context" aria-label="OHLC values">{formatOhlc(hovered ?? latest)}</div>}
    {candles.length > 0 ? <TradingChart candles={candles} levels={levels} onOhlcChange={onOhlcChange} /> : <div className="atlas-chart-empty"><strong>Market data unavailable</strong><span>ATLAS will render candles when the backend returns a valid series.</span></div>}
  </section>;
}
