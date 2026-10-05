import { requestJson } from "./client";
import { mapCandles } from "./mappers";
import type { Candle } from "./types";
export async function getCandles(symbol: string, interval: string, limit = 100): Promise<Candle[]> {
  const params = new URLSearchParams({ interval, limit: String(limit) });
  return mapCandles(await requestJson<unknown>(`/market/${encodeURIComponent(symbol)}/candles?${params}`));
}
