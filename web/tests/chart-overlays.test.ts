import { describe, expect, it } from "vitest";
import { toChartCandles, toPriceLines, toSignalMarkers } from "../features/chart/chart-overlays";
import type { Candle } from "../lib/api/types";
const candles: Candle[] = [{ time: 2, open: 1, high: 3, low: 0, close: 2, volume: 1 }, { time: 1, open: 2, high: 3, low: 1, close: 2, volume: null }, { time: 1, open: 2, high: 3, low: 1, close: 2, volume: null }];
describe("chart overlays", () => {
  it("sorts ascending and deterministically removes duplicate timestamps", () => { expect(toChartCandles(candles).map(c => c.time)).toEqual([1, 2]); });
  it("keeps empty candle sets empty", () => { expect(toChartCandles([])).toEqual([]); });
  it("maps entry, stop, and target to labeled lines", () => { expect(toPriceLines({ entry: 10, stopLoss: 9, takeProfit: 12 })).toEqual([{ price: 10, title: "Entry" }, { price: 9, title: "Stop loss" }, { price: 12, title: "Take profit" }]); });
  it("maps supplied signal events only", () => { expect(toSignalMarkers([{ time: 2, side: "BUY", label: "Buy" }])).toHaveLength(1); });
});
