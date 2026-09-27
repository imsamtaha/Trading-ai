"use client";

import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, createChart, type CandlestickData, type UTCTimestamp } from "lightweight-charts";
import type { Candle } from "@/lib/api/types";
import { normalizeCandles, toPriceLines, type TradeLevels } from "./chart-overlays";

export function TradingChart({ candles, levels = {} }: { candles: Candle[]; levels?: TradeLevels }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || candles.length === 0) return;
    const chart = createChart(ref.current, { autoSize: true, layout: { background: { type: ColorType.Solid, color: "#0b0e13" }, textColor: "#8d96a5" }, grid: { vertLines: { color: "#1c222b" }, horzLines: { color: "#1c222b" } } });
    const series = chart.addSeries(CandlestickSeries, { upColor: "#ff7417", downColor: "#5b6471", borderVisible: false, wickUpColor: "#ff9b58", wickDownColor: "#7a8491" });
    const data: CandlestickData[] = normalizeCandles(candles).map((c) => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }));
    series.setData(data);
    for (const line of toPriceLines(levels)) series.createPriceLine({ price: line.price, title: line.title, color: line.title === "Stop" ? "#f2a34a" : "#ff7417", lineWidth: 1, axisLabelVisible: true });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles, levels]);
  return <div ref={ref} className="atlas-chart-canvas" aria-label="ATLAS trading chart" />;
}
