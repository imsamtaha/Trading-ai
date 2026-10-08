import { describe, expect, it } from "vitest";
import { mapCandles, mapDashboardState, mapPrivateDashboardState } from "@/lib/api/mappers";

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

  it("maps only signed-in user scoped MT5 data", () => {
    const state = mapPrivateDashboardState({ plan: "FREE", mt5: { connected: true, account: { account_masked: "***4321", account_type: "DEMO", balance: 200, equity: 205 }, floating_position_pnl: 5, positions: [{ symbol: "EURUSD", profit: 5 }], symbols: [{ symbol: "EURUSD", price: 1.2 }] } });
    expect(state.connection).toBe("connected");
    expect(state.account).toMatchObject({ id: "***4321", mode: "DEMO", balance: 200, floatingPnl: 5 });
    expect(state.positions).toHaveLength(1);
    expect(state.risk.overall).toBeNull();
    expect(mapPrivateDashboardState({ mt5: { connected: false, account: { balance: 99 } } }).account.balance).toBeNull();
    const unconnected = mapPrivateDashboardState({ user: { email: "trader@example.com" }, features: { trading_intelligence: false }, mt5: { connected: false } });
    expect(unconnected.userEmail).toBe("trader@example.com");
    expect(unconnected.entitlements?.tradingIntelligence).toBe(false);
    expect(mapPrivateDashboardState({ features: { trading_intelligence: true }, mt5: { connected: false } }).entitlements?.tradingIntelligence).toBe(true);
  });

  it("filters malformed candle points", () => {
    const candles = mapCandles([{ time: 1, open: 10, high: 12, low: 9, close: 11 }, { time: "bad", open: 1 }]);
    expect(candles).toEqual([{ time: 1, open: 10, high: 12, low: 9, close: 11 }]);
  });
});

// OWNER role regression coverage
it("preserves owner role from the private dashboard payload", () => {
  const state = mapPrivateDashboardState({
    user: { email: "owner@example.com", role: "OWNER" },
    features: { trading_intelligence: true },
    mt5: { connected: false },
  });
  expect(state.userRole).toBe("OWNER");
});

 it("shows closed MT5 trades with the configured server time offset", () => {
  const state = mapPrivateDashboardState({ mt5: { connected: true, account: { account_masked: "***1391", currency: "USD" }, history_time_offset_seconds: 10800, recent_trades: [{ symbol: "EURUSD", position_id: 349264740, profit: 3, time: 1790884493 }] } });
  expect(state.activity?.[0].message).toContain("#349264740");
  expect(state.activity?.[0].timestamp).toBe("2026-10-01T16:54:53.000Z");
 });
