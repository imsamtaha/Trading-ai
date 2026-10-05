"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import { createChart, CandlestickSeries, createSeriesMarkers } from "lightweight-charts";
import type { Candle } from "../../lib/api/types";
import { toChartCandles, toPriceLines, toSignalMarkers, type ChartMarkerInput, type ChartPriceLevel } from "./chart-overlays";
const EMPTY_SIGNALS: ChartMarkerInput[] = [];
const EMPTY_LEVELS: ChartPriceLevel = {};
export function TradingChart({ candles, symbol, timeframe, signals = EMPTY_SIGNALS, levels = EMPTY_LEVELS }: { candles: Candle[]; symbol: string; timeframe: string; signals?: ChartMarkerInput[]; levels?: ChartPriceLevel }): ReactElement {
  const mount = useRef<HTMLDivElement>(null); const [ohlc, setOhlc] = useState<Candle | null>(null); const points = useMemo(() => toChartCandles(candles), [candles]);
  useEffect(() => {
    if (!mount.current || !points.length) return;
    const chart = createChart(mount.current, { autoSize: true, layout: { background: { color: "#151719" }, textColor: "#a3a49f" }, grid: { vertLines: { color: "#242629" }, horzLines: { color: "#242629" } }, rightPriceScale: { borderColor: "#343638" }, timeScale: { borderColor: "#343638", timeVisible: true }, crosshair: { mode: 0 } });
    const series = chart.addSeries(CandlestickSeries, { upColor: "#74c69d", downColor: "#ed7272", borderVisible: false, wickUpColor: "#74c69d", wickDownColor: "#ed7272" });
    series.setData(points.map(p => ({ time: p.time as never, open: p.open, high: p.high, low: p.low, close: p.close })));
    createSeriesMarkers(series, toSignalMarkers(signals));
    for (const level of toPriceLines(levels)) series.createPriceLine({ price: level.price, title: level.title, color: level.title === "Stop loss" ? "#ed7272" : level.title === "Take profit" ? "#74c69d" : "#f28a23", lineWidth: 1, lineStyle: 2, axisLabelVisible: true });
    chart.subscribeCrosshairMove(param => { const item = param.seriesData.get(series) as { open: number; high: number; low: number; close: number } | undefined; if (item) setOhlc({ ...points[0], open: item.open, high: item.high, low: item.low, close: item.close }); });
    chart.timeScale().fitContent(); return () => chart.remove();
  }, [points, symbol, timeframe, signals, levels]);
  return <div className="atlas-chart-frame"><div className="atlas-chart-readout">{symbol} · {timeframe} {ohlc && <span>O {ohlc.open} H {ohlc.high} L {ohlc.low} C {ohlc.close}</span>}</div>{points.length ? <div className="atlas-chart-canvas" ref={mount} aria-label={`${symbol} ${timeframe} candlestick chart`} /> : <div className="atlas-chart-empty">Market data is unavailable for {symbol} at {timeframe}.</div>}</div>;
}
