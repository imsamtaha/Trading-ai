export type ConnectionState = "online" | "offline" | "unknown";
export interface Position { symbol: string; direction: string | null; volume: number | null; priceOpen: number | null; stopLoss: number | null; takeProfit: number | null; profit: number | null }
export interface Candle { time: number; open: number; high: number; low: number; close: number; volume: number | null }
export interface AccountViewModel { currency: string | null; balance: number | null; equity: number | null; floatingPnl: number | null }
export interface RiskViewModel { level: string | null; dailyLossUsage: number | null; drawdown: number | null; exposure: number | null; positionSizeUtilization: number | null; aggregateOpenRisk: number | null; warnings: string[]; protection: string | null }
export interface MarketTile { label: string; category: string | null; price: number | null; changePercent: number | null; marketState: string | null }
export interface DashboardSignal { symbol: string; type: string; message: string }
export interface DashboardViewModel { signals: DashboardSignal[]; markets: MarketTile[]; connection: ConnectionState; mode: string | null; account: AccountViewModel; positions: Position[]; openPositions: number | null; floatingPnl: number | null; risk: RiskViewModel | null; timestamp: string | null }
export interface AgentChatRequest { request: string; interval?: string; multi_timeframe?: boolean; account_balance?: number; risk_percent?: number }
export interface AgentChatResponse { [key: string]: unknown }
export interface BackendDashboardDto { [key: string]: unknown; account?: Record<string, unknown> | null; positions?: unknown; risk?: Record<string, unknown> | null }
