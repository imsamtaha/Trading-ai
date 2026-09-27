export type ConnectionState = "connected" | "offline" | "unknown";
export type Candle = { time: number; open: number; high: number; low: number; close: number };
export type Position = { symbol: string; direction?: string; size?: number | null; entry?: number | null; current?: number | null; pnl?: number | null; stopLoss?: number | null; takeProfit?: number | null; status?: string };
export type RiskViewModel = { overall: number | null; dailyLoss: number | null; drawdown: number | null; exposure: number | null; positionSize: number | null; aggregateOpenRisk: number | null; protectionState: string | null; warnings: string[] };
export type AccountViewModel = { id: string | null; mode: string | null; balance: number | null; equity: number | null; floatingPnl: number | null; dailyPnl: number | null; marginFree: number | null };
export type DashboardViewModel = { connection: ConnectionState; account: AccountViewModel; risk: RiskViewModel; positions: Position[]; markets: Array<{ symbol: string; price: number | null; changePct: number | null }> };
export type AgentChatRequest = { message: string; context?: Record<string, unknown> };
export type AgentChatResponse = { message: string };
