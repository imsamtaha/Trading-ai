import { describe, expect, it } from "vitest";
import { mapCandles, mapDashboardState, mapPositions } from "../lib/api/mappers";

describe("backend response mapping", () => {
  it("maps a complete account and dashboard snapshot", () => {
    const result = mapDashboardState({ status: "ONLINE", mode: "READ_ONLY", account: { currency: "USD", balance: 12000, equity: 12100, floating_profit: 100 }, open_positions: 2, floating_position_pnl: 100, positions: [{ symbol: "EURUSD", direction: "BUY", volume: 0.1, profit: 100 }], risk: { level: "LOW" } });
    expect(result.connection).toBe("online");
    expect(result.mode).toBe("READ_ONLY");
    expect(result.account).toEqual(expect.objectContaining({ currency: "USD", balance: 12000, equity: 12100, floatingPnl: 100 }));
    expect(result.positions).toHaveLength(1);
  });
  it("keeps absent equity, P/L, and risk values null", () => {
    const result = mapDashboardState({ status: "ONLINE", account: { balance: 100 } });
    expect(result.account.equity).toBeNull();
    expect(result.account.floatingPnl).toBeNull();
    expect(result.risk).toBeNull();
  });
  it("uses unknown connection for missing state and accepts empty positions", () => {
    expect(mapDashboardState({}).connection).toBe("unknown");
    expect(mapPositions({ positions: [] })).toEqual([]);
  });
  it("skips malformed candle entries", () => {
    expect(mapCandles({ candles: [{ open_time: "2026-01-01T00:00:00Z", open: 1, high: 2, low: 0.5, close: 1.5, volume: 5 }, { open_time: "bad", close: 1 }, null] })).toHaveLength(1);
  });
});
