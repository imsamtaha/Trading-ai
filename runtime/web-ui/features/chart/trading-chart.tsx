"use client";

import { useEffect, useRef } from "react";
import { AreaSeries, CandlestickSeries, ColorType, LineSeries, createChart, type LineData, type Time, type UTCTimestamp } from "lightweight-charts";
import type { Candle } from "@/lib/api/types";
import { normalizeCandles, toPriceLines, type TradeLevels } from "./chart-overlays";
import { ema, sma, type IndicatorId } from "./indicators";

export type ChartMode = "area" | "candles";

export function TradingChart({ candles, levels = {}, indicators = [], onOhlcChange, mode = "area" }: { candles: Candle[]; levels?: TradeLevels; indicators?: IndicatorId[]; onOhlcChange?: (candle: Candle | null) => void; mode?: ChartMode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || candles.length === 0) return;
    const normalized = normalizeCandles(candles);
    const chart = createChart(ref.current, { autoSize: true, layout: { background: { type: ColorType.Solid, color: "#091a30" }, textColor: "#b9d4ed" }, grid: { vertLines: { color: "#1e3955" }, horzLines: { color: "#1e3955" } } });
    const series = mode === "area" ? (() => {
      const area = chart.addSeries(AreaSeries, { lineColor: "#ff943e", topColor: "#ed610b99", bottomColor: "#ed610b08", lineWidth: 2 });
      area.setData(normalized.map((c) => ({ time: c.time as UTCTimestamp, value: c.close })));
      return area;
    })() : (() => {
      const bars = chart.addSeries(CandlestickSeries, { upColor: "#ff7417", downColor: "#b19a8b", borderVisible: false, wickUpColor: "#ff9b58", wickDownColor: "#b19a8b" });
      bars.setData(normalized.map((c) => ({ ...c, time: c.time as UTCTimestamp })));
      return bars;
    })();
    const addLine = (values: (number | null)[], color: string) => { const line = chart.addSeries(LineSeries, { color, lineWidth: 2, priceLineVisible: false, lastValueVisible: false }); line.setData(values.flatMap((value, i) => value == null ? [] : [{ time: normalized[i].time as UTCTimestamp, value } as LineData])); };
    if (indicators.includes("ema20")) addLine(ema(normalized, 20), "#ffb067");
    if (indicators.includes("sma50")) addLine(sma(normalized, 50), "#f1eee8");
    const byTime = new Map(normalized.map((candle) => [candle.time, candle]));
    const crosshair = ({ time }: { time?: Time }) => onOhlcChange?.(typeof time === "number" ? byTime.get(time) ?? null : null);
    chart.subscribeCrosshairMove(crosshair);
    for (const line of toPriceLines(levels)) series.createPriceLine({ price: line.price, title: line.title, color: line.title === "Stop" ? "#f2a34a" : "#ff7417", lineWidth: 1, axisLabelVisible: true });
    chart.timeScale().fitContent();
    return () => { chart.unsubscribeCrosshairMove(crosshair); chart.remove(); };
  }, [candles, levels, indicators, onOhlcChange, mode]);
  return <div ref={ref} className="atlas-chart-canvas" aria-label="ATLAS trading chart" />;
}
