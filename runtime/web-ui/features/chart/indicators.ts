import type { Candle } from "@/lib/api/types";

export type IndicatorId = "ema20" | "sma50" | "rsi14";
export const indicatorLabels: Record<IndicatorId, string> = {
  ema20: "EMA 20",
  sma50: "SMA 50",
  rsi14: "RSI 14",
};

export function sma(candles: Candle[], period: number) {
  return candles.map((c, i) => i + 1 < period ? null : candles.slice(i + 1 - period, i + 1).reduce((n, x) => n + x.close, 0) / period);
}

export function ema(candles: Candle[], period: number) {
  if (!candles.length) return [];
  const k = 2 / (period + 1); let value = candles[0].close;
  return candles.map((c, i) => { value = i ? c.close * k + value * (1 - k) : value; return value; });
}

export function rsi(candles: Candle[], period = 14) {
  return candles.map((_, i) => {
    if (i < period) return null;
    const moves = candles.slice(i - period, i + 1).slice(1).map((c, j) => c.close - candles[i - period + j].close);
    const gain = moves.reduce((n, x) => n + Math.max(x, 0), 0) / period;
    const loss = moves.reduce((n, x) => n + Math.max(-x, 0), 0) / period;
    return loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  });
}
