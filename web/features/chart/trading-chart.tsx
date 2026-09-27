"use client";

import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, createChart, type CandlestickData, type UTCTimestamp } from "lightweight-charts";
import type { Candle } from "@/lib/api/types";
import { normalizeCandles, toPriceLines, type TradeLevels } from "./chart-overlays";

export function TradingChart({ candles, levels = {}, onOhlcChange }: { candles: Candle[]; levels?: TradeLevels; onOhlcChange?: (candle: Candle | null) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || candles.length === 0) return;
    const chart = createChart(ref.current, { autoSize: true, layout: { background: { type: ColorType.Solid, color: "#0b0e13" }, textColor: "#8d96a5" }, grid: { vertLines: { color: "#1c222b" }, horzLines: { color: "#1c222b" } } });
    const series = chart.addSeries(CandlestickSeries, { upColor: "#ff7417", downColor: "#5b6471", borderVisible: false, wickUpColor: "#ff9b58", wickDownColor: "#7a8491" });
    const data: CandlestickData[] = normalizeCandles(candles).map((c) => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }));
    series.setData(data);
    const crosshair = (param: { seriesData: Map<unknown, unknown> }) => {
      const bar = param.seriesData.get(series) as CandlestickData | undefined;
      onOhlcChange?.(bar && "open" in bar ? { time: Number(bar.time), open: bar.open, high: bar.high, low: bar.low, close: bar.close } : null);
    };
    chart.subscribeCrosshairMove(crosshair);
    for (const line of toPriceLines(levels)) series.createPriceLine({ price: line.price, title: line.title, color: line.title === "Stop" ? "#f2a34a" : "#ff7417", lineWidth: 1, axisLabelVisible: true });
    chart.timeScale().fitContent();
    return () => { chart.unsubscribeCrosshairMove(crosshair); chart.remove(); };
  }, [candles, levels, onOhlcChange]);
  return <div ref={ref} className="atlas-chart-canvas" aria-label="ATLAS trading chart" />;
}
