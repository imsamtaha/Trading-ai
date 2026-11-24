import type { DashboardViewModel } from "./types";

export const DASHBOARD_FIXTURE: DashboardViewModel = {
  connection: "connected",
  account: { id: "***2481", mode: "DEMO", balance: 10000, equity: 10248.42, floatingPnl: 248.42, dailyPnl: 118.2, marginFree: 8900 },
  risk: { overall: 28, dailyLoss: 12, drawdown: 4, exposure: 28, positionSize: 36, aggregateOpenRisk: 22, protectionState: "Protected", warnings: [] },
  positions: [{ symbol: "BTCUSDT", direction: "LONG", size: 0.5, entry: 66420, current: 67432.18, pnl: 506.09, stopLoss: 65500, takeProfit: 69000, status: "OPEN" }],
  markets: [
    { symbol: "EURUSD", price: 1.0734, changePct: 0.21 },
    { symbol: "GBPUSD", price: 1.2498, changePct: 0.18 },
    { symbol: "XAUUSD", price: 2518.32, changePct: 0.45 },
  ],
};
