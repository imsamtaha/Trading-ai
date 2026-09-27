import { atlasFetch } from "./client";
import { mapCandles } from "./mappers";
import type { Candle } from "./types";

export async function getCandles(symbol: string, interval: string, limit = 120): Promise<Candle[]> {
  const endpoint = `/market/${encodeURIComponent(symbol)}/candles?interval=${encodeURIComponent(interval)}&limit=${limit}`;
  const raw = await atlasFetch<unknown>(endpoint);
  if (raw && typeof raw === "object" && !Array.isArray(raw) && "candles" in raw) {
    return mapCandles((raw as Record<string, unknown>).candles);
  }
  return mapCandles(raw);
}
