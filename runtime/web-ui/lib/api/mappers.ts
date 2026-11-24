import type { Candle, DashboardViewModel, Position } from "./types";
type Obj = Record<string, unknown>;
const obj = (value: unknown): Obj => value && typeof value === "object" && !Array.isArray(value) ? value as Obj : {};
const num = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const str = (value: unknown): string | null => typeof value === "string" && value.trim() ? value : null;
export function mapDashboardState(input: unknown): DashboardViewModel {
  const root = obj(input), account = obj(root.account), risk = obj(root.risk);
  const status = str(root.status ?? root.connection)?.toLowerCase();
  const connection = status === "online" || status === "connected" ? "connected" : status === "offline" ? "offline" : "unknown";
  const symbols = Array.isArray(root.symbols) ? root.symbols.map(obj) : [];
  const rawMarkets = Array.isArray(root.markets) ? root.markets.map(obj) : symbols;
  const markets = rawMarkets.map((m) => ({ symbol: str(m.symbol) ?? "", price: num(m.price), changePct: num(m.change_pct ?? m.changePct) })).filter((m) => m.symbol);
  const signals = symbols.map((s) => ({ symbol: str(s.symbol) ?? "", direction: str(obj(s.decision).decision) ?? "UNKNOWN", confidence: num(obj(s.quality).execution_confidence), rationale: str(obj(s.decision).rationale), riskWarning: str(obj(s.quality).risk_warning), timestamp: str(s.timestamp) })).filter((s) => s.symbol && ["BUY","SELL"].includes(s.direction));
  const activity = Array.isArray(root.alerts) ? root.alerts.map(obj).map((a) => ({ message: str(a.message) ?? "", timestamp: str(a.timestamp) })).filter((a) => a.message) : [];
  return {
    connection,
    account: { id: str(account.login ?? account.id), mode: str(account.account_type ?? account.mode ?? root.mode), balance: num(account.balance), equity: num(account.equity), floatingPnl: num(account.floating_profit ?? account.floating_pnl ?? account.floatingPnl), dailyPnl: num(account.daily_pnl ?? account.dailyPnl), marginFree: num(account.margin_free ?? account.marginFree) },
    risk: { overall: num(risk.overall ?? risk.overall_risk), dailyLoss: num(risk.daily_loss ?? risk.dailyLoss), drawdown: num(risk.drawdown), exposure: num(risk.exposure), positionSize: num(risk.position_size ?? risk.positionSize), aggregateOpenRisk: num(risk.aggregate_open_risk ?? risk.aggregateOpenRisk), protectionState: str(risk.protection_state ?? risk.protectionState), warnings: Array.isArray(risk.warnings) ? risk.warnings.filter((x): x is string => typeof x === "string") : [] },
    positions: mapPositions(root.positions), markets, signals, activity,
  };
}
export function mapPrivateDashboardState(input: unknown): DashboardViewModel {
  const root = obj(input), mt5 = obj(root.mt5), user = obj(root.user), features = obj(root.features);
  const identity = { userEmail: str(user.email), userRole: str(user.role)?.toUpperCase() ?? null, entitlements: { tradingIntelligence: features.trading_intelligence === true } };
  if (mt5.connected !== true) return { ...mapDashboardState({ status: "OFFLINE" }), ...identity };
  const account = obj(mt5.account);
  const state = mapDashboardState({
    status: "ONLINE",
    account: { login: account.account_masked, account_type: account.account_type, balance: account.balance, equity: account.equity, floating_profit: mt5.floating_position_pnl },
    positions: mt5.positions,
    markets: mt5.symbols,
    alerts: Array.isArray(mt5.recent_trades) ? mt5.recent_trades.map(obj).map((trade) => ({
      message: `${str(trade.symbol) ?? "MT5"} · #${num(trade.position_id) ?? num(trade.ticket) ?? ""} · ${num(trade.profit) ?? 0} ${str(account.currency) ?? ""}`,
      timestamp: num(trade.time) !== null ? new Date(((num(trade.time) ?? 0) - (num(mt5.history_time_offset_seconds) ?? 0)) * 1000).toISOString() : null,
    })) : [],
  });
  return { ...(state.account.id ? state : mapDashboardState({ status: "OFFLINE" })), ...identity };
}

export function mapPositions(input: unknown): Position[] {
  if (!Array.isArray(input)) return [];
  return input.map(obj).filter((p) => typeof p.symbol === "string").map((p) => ({ symbol: String(p.symbol), direction: str(p.direction) ?? undefined, size: num(p.size ?? p.volume), entry: num(p.entry ?? p.entry_price ?? p.price_open), current: num(p.current ?? p.current_price), pnl: num(p.pnl ?? p.profit), stopLoss: num(p.stop_loss ?? p.stopLoss ?? p.sl), takeProfit: num(p.take_profit ?? p.takeProfit ?? p.tp), status: str(p.status) ?? undefined }));
}
export function mapCandles(input: unknown): Candle[] {
  if (!Array.isArray(input)) return [];
  return input.map(obj).filter((c) => [c.time ?? c.open_time,c.open,c.high,c.low,c.close].every((v) => typeof v === "number" && Number.isFinite(v))).map((c) => ({ time: c.time as number ?? Math.floor((c.open_time as number) / 1000), open: c.open as number, high: c.high as number, low: c.low as number, close: c.close as number }));
}
