import type { AccountViewModel, Candle, ConnectionState, DashboardViewModel, DashboardSignal, MarketTile, Position, RiskViewModel } from "./types";
type Row = Record<string, unknown>;
const row = (value: unknown): Row => value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
const numberOrNull = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const stringOrNull = (value: unknown): string | null => typeof value === "string" && value.length ? value : null;
const numeric = (source: Row, ...keys: string[]) => { for (const key of keys) { const n = numberOrNull(source[key]); if (n !== null) return n; } return null; };
export function mapPosition(value: unknown): Position {
  const p = row(value);
  return { symbol: stringOrNull(p.symbol) ?? "—", direction: stringOrNull(p.direction), volume: numeric(p, "volume"), priceOpen: numeric(p, "price_open", "priceOpen"), stopLoss: numeric(p, "sl", "stop_loss"), takeProfit: numeric(p, "tp", "take_profit"), profit: numeric(p, "profit") };
}
export function mapPositions(value: unknown): Position[] {
  const entries = Array.isArray(value) ? value : Array.isArray(row(value).positions) ? row(value).positions as unknown[] : [];
  return entries.filter(item => item && typeof item === "object" && !Array.isArray(item)).map(mapPosition);
}
function mapRisk(value: unknown): RiskViewModel | null {
  if (!value || typeof value !== "object") return null;
  const r = row(value);
  return { level: stringOrNull(r.level ?? r.overall_risk), dailyLossUsage: numeric(r, "daily_loss_usage", "daily_loss_used_percent"), drawdown: numeric(r, "drawdown", "drawdown_percent"), exposure: numeric(r, "exposure", "exposure_percent"), positionSizeUtilization: numeric(r, "position_size_utilization"), aggregateOpenRisk: numeric(r, "aggregate_open_risk"), warnings: Array.isArray(r.warnings) ? r.warnings.filter((x): x is string => typeof x === "string") : [], protection: stringOrNull(r.protection ?? r.protection_state) };
}
export function mapDashboardState(value: unknown): DashboardViewModel {
  const source = row(value); const account = row(source.account);
  const status = typeof source.status === "string" ? source.status.toLowerCase() : "";
  const connection: ConnectionState = status === "online" || status === "connected" ? "online" : status === "offline" || status === "disconnected" ? "offline" : "unknown";
  const accountModel: AccountViewModel = { currency: stringOrNull(account.currency), balance: numeric(account, "balance"), equity: numeric(account, "equity"), floatingPnl: numeric(account, "floating_profit", "floating_pnl") };
  const alerts = Array.isArray(source.alerts) ? source.alerts : [];
  const signals: DashboardSignal[] = alerts.filter(item => item && typeof item === "object").map(item => { const a = row(item); return { symbol: stringOrNull(a.symbol) ?? "—", type: stringOrNull(a.type) ?? "activity", message: stringOrNull(a.message) ?? "" }; }).filter(signal => signal.message.length > 0);
  const board = row(source.financial_market).market_board;
  const markets: MarketTile[] = Array.isArray(board) ? board.filter(item => item && typeof item === "object").map(item => { const m = row(item); return { label: stringOrNull(m.label ?? m.symbol) ?? "Market", category: stringOrNull(m.category), price: numeric(m, "price"), changePercent: numeric(m, "change_percent"), marketState: stringOrNull(m.market_state) }; }) : [];
  return { signals, markets, connection, mode: stringOrNull(source.mode), account: accountModel, positions: mapPositions(source.positions), openPositions: numeric(source, "open_positions"), floatingPnl: numeric(source, "floating_position_pnl") ?? accountModel.floatingPnl, risk: mapRisk(source.risk), timestamp: stringOrNull(source.timestamp) };
}
export function mapCandles(value: unknown): Candle[] {
  const items = Array.isArray(value) ? value : Array.isArray(row(value).candles) ? row(value).candles as unknown[] : [];
  return items.flatMap(item => {
    const c = row(item); const rawTime = c.open_time ?? c.time ?? c.timestamp;
    const parsed = typeof rawTime === "number" ? rawTime : typeof rawTime === "string" ? Date.parse(rawTime) / 1000 : NaN;
    const open = numberOrNull(c.open), high = numberOrNull(c.high), low = numberOrNull(c.low), close = numberOrNull(c.close);
    if (!Number.isFinite(parsed) || open === null || high === null || low === null || close === null || high < low) return [];
    return [{ time: parsed, open, high, low, close, volume: numeric(c, "volume", "tick_volume") }];
  });
}
