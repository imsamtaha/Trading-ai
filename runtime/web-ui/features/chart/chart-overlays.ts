import type { Candle } from "@/lib/api/types";

export type TradeLevels = { entry?: number | null; stopLoss?: number | null; takeProfit?: number | null };
const formatPrice = new Intl.NumberFormat("en-US", { useGrouping: false, maximumFractionDigits: 8 });
export function formatOhlc(candle: Candle): string {
  return `O ${formatPrice.format(candle.open)} · H ${formatPrice.format(candle.high)} · L ${formatPrice.format(candle.low)} · C ${formatPrice.format(candle.close)}`;
}

export type PriceLine = { title: "Entry" | "Stop" | "Target"; price: number };

export function normalizeCandles(candles: Candle[]): Candle[] {
  const byTime = new Map<number, Candle>();
  for (const candle of candles) if (!byTime.has(candle.time)) byTime.set(candle.time, candle);
  return [...byTime.values()].sort((a, b) => a.time - b.time);
}

export function toPriceLines(levels: TradeLevels): PriceLine[] {
  const result: PriceLine[] = [];
  if (typeof levels.entry === "number" && Number.isFinite(levels.entry)) result.push({ title: "Entry", price: levels.entry });
  if (typeof levels.stopLoss === "number" && Number.isFinite(levels.stopLoss)) result.push({ title: "Stop", price: levels.stopLoss });
  if (typeof levels.takeProfit === "number" && Number.isFinite(levels.takeProfit)) result.push({ title: "Target", price: levels.takeProfit });
  return result;
}
