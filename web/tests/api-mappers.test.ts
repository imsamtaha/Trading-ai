import { describe, expect, it } from "vitest";
import { mapCandles, mapDashboardState } from "@/lib/api/mappers";

describe("ATLAS API mappers", () => {
  it("maps missing account and risk fields safely", () => {
    const state = mapDashboardState({ account: { balance: 10000 }, positions: [] });
    expect(state.account.balance).toBe(10000);
    expect(state.account.equity).toBeNull();
    expect(state.account.floatingPnl).toBeNull();
    expect(state.connection).toBe("unknown");
    expect(state.risk.overall).toBeNull();
    expect(state.positions).toEqual([]);
  });

  it("filters malformed candle points", () => {
    const candles = mapCandles([{ time: 1, open: 10, high: 12, low: 9, close: 11 }, { time: "bad", open: 1 }]);
    expect(candles).toEqual([{ time: 1, open: 10, high: 12, low: 9, close: 11 }]);
  });
});
