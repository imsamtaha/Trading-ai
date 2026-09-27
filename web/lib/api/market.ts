import { atlasFetch } from "./client";
import { apiPath } from "./config";
import { mapCandles } from "./mappers";
import type { Candle } from "./types";
export async function getCandles(symbol: string, interval: string, limit = 120): Promise<Candle[]> {
  const endpoint = apiPath(`/api/user/chart-data?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${limit}`);
  const raw = await atlasFetch<{candles?: unknown}>(endpoint, { cache: "no-store", credentials: "same-origin" });
  return mapCandles(raw?.candles);
}
