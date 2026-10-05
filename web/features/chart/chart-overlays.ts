import type { Candle } from "../../lib/api/types";
export interface ChartMarkerInput { time: number; side: string; label?: string }
export interface ChartPriceLevel { entry?: number | null; stopLoss?: number | null; takeProfit?: number | null }
export function toChartCandles(candles: Candle[]): Candle[] {
  const unique = new Map<number, Candle>(); for (const candle of candles) if (Number.isFinite(candle.time) && !unique.has(candle.time)) unique.set(candle.time, candle);
  return [...unique.values()].sort((a, b) => a.time - b.time);
}
export function toPriceLines(levels: ChartPriceLevel): { price: number; title: string }[] {
  return ([ [levels.entry, "Entry"], [levels.stopLoss, "Stop loss"], [levels.takeProfit, "Take profit"] ] as const).flatMap(([price, title]) => typeof price === "number" && Number.isFinite(price) ? [{ price, title }] : []);
}
export function toSignalMarkers(markers: ChartMarkerInput[]) { return markers.filter(m => Number.isFinite(m.time) && ["BUY", "SELL"].includes(m.side.toUpperCase())).map(m => ({ time: m.time as never, position: m.side.toUpperCase() === "BUY" ? "belowBar" as const : "aboveBar" as const, color: m.side.toUpperCase() === "BUY" ? "#74c69d" : "#ff8585", shape: m.side.toUpperCase() === "BUY" ? "arrowUp" as const : "arrowDown" as const, text: m.label ?? m.side })); }
