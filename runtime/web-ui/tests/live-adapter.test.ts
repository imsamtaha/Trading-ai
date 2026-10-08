import { afterEach, describe, expect, it, vi } from "vitest";
import { getDashboardState } from "@/lib/api/dashboard";
import { sendAgentMessage } from "@/lib/api/agent";
import { getCandles } from "@/lib/api/market";
import { mapDashboardState } from "@/lib/api/mappers";
afterEach(() => vi.unstubAllGlobals());
describe("live FastAPI adapter", () => {
  it("maps dashboard/atlas account, symbols, positions and alerts without invented risk", () => {
    const state = mapDashboardState({ status: "ONLINE", mode: "READ_ONLY", account: { login: "***1234", account_type: "REAL", balance: 110, equity: 115, floating_profit: 5 }, symbols: [{ symbol: "XAUUSD", price: 2510, decision: { decision: "BUY" }, quality: { execution_confidence: 72 } }], positions: [{ symbol: "XAUUSD", direction: "BUY", volume: 0.1, price_open: 2500, sl: 2480, tp: 2550, profit: 10 }] });
    expect(state.connection).toBe("connected");
    expect(state.account).toMatchObject({ id: "***1234", mode: "REAL", floatingPnl: 5 });
    expect(state.positions[0]).toMatchObject({ size: 0.1, entry: 2500, stopLoss: 2480, pnl: 10 });
    expect(state.markets[0].symbol).toBe("XAUUSD");
    expect(state.risk.overall).toBeNull();
  });
  it("uses the authenticated user dashboard endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({mt5:{connected:true,account:{account_masked:"***1234",balance:21}}}),{status:200}));
    vi.stubGlobal("fetch", fetcher);
    expect((await getDashboardState()).account.balance).toBe(21);
    expect(fetcher.mock.calls[0][0]).toBe("/backend/api/user/dashboard");
    expect(fetcher.mock.calls[0][1].credentials).toBe("same-origin");
  });
  it("sends an authenticated private message and rejects missing assistant answers", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({message:"Context only"}),{status:200})).mockResolvedValueOnce(new Response(JSON.stringify({result:{}}),{status:200}));
    vi.stubGlobal("fetch", fetcher);
    expect((await sendAgentMessage({message:"Explain risk"})).message).toBe("Context only");
    expect(fetcher.mock.calls[0][0]).toBe("/backend/api/user/assistant");
    expect(fetcher.mock.calls[0][1].credentials).toBe("same-origin");
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({message:"Explain risk"});
    await expect(sendAgentMessage({message:"Again"})).rejects.toThrow("answer");
  });
  it("reads chart data through backend allowlist", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({candles:[]}),{status:200}));
    vi.stubGlobal("fetch", fetcher);
    await getCandles("XAUUSD","15m");
    expect(fetcher.mock.calls[0][0]).toBe("/backend/api/user/chart-data?symbol=XAUUSD&interval=15m&limit=120");
  });
  it("normalizes FastAPI open_time milliseconds into chart seconds", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({candles:[{open_time:1700000000000,open:1,high:2,low:1,close:2}]}),{status:200})));
    expect(await getCandles("XAUUSD","1h")).toEqual([{time:1700000000,open:1,high:2,low:1,close:2}]);
  });
});
