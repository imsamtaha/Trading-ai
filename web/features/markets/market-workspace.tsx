"use client";

import { useCallback, useState } from "react";
import type { Candle } from "@/lib/api/types";
import type { SignalView } from "@/features/signals/signals-panel";
import { ChartToolbar } from "@/features/chart/chart-toolbar";
import { TradingChart } from "@/features/chart/trading-chart";
import { formatOhlc, toPriceLines, type TradeLevels } from "@/features/chart/chart-overlays";
import { rsi, type IndicatorId } from "@/features/chart/indicators";
import { AgentBadge } from "@/components/system/agent-badge";
export function MarketWorkspace({ candles, symbol, timeframe, levels = {}, signal, onChange }: {
  candles: Candle[]; symbol: string; timeframe: string; levels?: TradeLevels; signal?: SignalView; onChange?: (symbol: string, timeframe: string) => void;
}) {
  const [hovered, setHovered] = useState<Candle | null>(null);
  const [indicators, setIndicators] = useState<IndicatorId[]>([]);
  const onOhlcChange = useCallback((candle: Candle | null) => setHovered(candle), []);
  const toggleIndicator = (id: IndicatorId) => setIndicators((items) => items.includes(id) ? items.filter((x) => x !== id) : [...items, id]);
  const priceLines = toPriceLines(levels); const latest = candles.length ? candles[candles.length - 1] : null;
  const latestRsi = indicators.includes("rsi14") ? [...rsi(candles, 14)].reverse().find((x) => x != null) : null;
  return <section className="atlas-card atlas-market-workspace" id="trade">
    <div className="atlas-sector-title"><span>Market</span><AgentBadge /></div>
    <ChartToolbar symbol={symbol} timeframe={timeframe} indicators={indicators} onIndicatorToggle={toggleIndicator} onChange={onChange} />
    {signal && <div className="atlas-chart-context" role="status">{signal.direction} signal{signal.confidence != null && ` · ${signal.confidence}% confidence`}</div>}
    {latestRsi != null && <div className="atlas-chart-context">RSI 14 · {latestRsi.toFixed(1)}</div>}
    {priceLines.length > 0 && <div className="atlas-chart-levels">{priceLines.map((line) => <span key={line.title}>{line.title} {line.price.toLocaleString("en-US", { maximumFractionDigits: 5 })}</span>)}</div>}
    {latest && <div className="atlas-chart-context" aria-label="OHLC values">{formatOhlc(hovered ?? latest)}</div>}
    {candles.length > 0 ? <TradingChart candles={candles} levels={levels} indicators={indicators} onOhlcChange={onOhlcChange} /> : <div className="atlas-chart-empty"><strong>Market data unavailable</strong><span>ATLAS will render candles when the backend returns a valid series.</span></div>}
  </section>;
}
