import { describe, expect, it } from "vitest";
import { normalizeCandles, toPriceLines } from "@/features/chart/chart-overlays";

describe("chart overlays", () => {
  it("sorts candles and removes duplicate timestamps", () => {
    const result = normalizeCandles([
      { time: 2, open: 2, high: 3, low: 1, close: 2.5 },
      { time: 1, open: 1, high: 2, low: .5, close: 1.5 },
      { time: 2, open: 9, high: 9, low: 9, close: 9 },
    ]);
    expect(result.map((c) => c.time)).toEqual([1, 2]);
    expect(result[1].close).toBe(2.5);
  });

  it("maps entry stop and target to labeled price lines", () => {
    expect(toPriceLines({ entry: 100, stopLoss: 95, takeProfit: 110 }).map((x) => x.title)).toEqual(["Entry", "Stop", "Target"]);
  });
});
