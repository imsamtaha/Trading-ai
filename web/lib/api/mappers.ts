import type { Candle, DashboardViewModel, Position } from "./types";

type Obj = Record<string, unknown>;
const obj = (value: unknown): Obj => value && typeof value === "object" && !Array.isArray(value) ? value as Obj : {};
const num = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const text = (value: unknown): string | null => typeof value === "string" && value.trim() ? value : null;

export function mapDashboardState(input: unknown): DashboardViewModel {
  const root = obj(input);
  const account = obj(root.account);
  const risk = obj(root.risk);
  const rawConnection = String(root.connection ?? root.status ?? "unknown").toLowerCase();
  const connection = rawConnection.includes("connect") ? "connected" : rawConnection.includes("off") ? "offline" : "unknown";
  const markets = Array.isArray(root.markets) ? root.markets.map(obj).map((m) => ({ symbol: String(m.symbol ?? ""), price: num(m.price), changePct: num(m.change_pct ?? m.changePct) })).filter((m) => m.symbol) : [];
  return {
    connection,
    account: { id: text(account.id), mode: text(account.mode ?? root.mode), balance: num(account.balance), equity: num(account.equity), floatingPnl: num(account.floating_pnl ?? account.floatingPnl), dailyPnl: num(account.daily_pnl ?? account.dailyPnl), marginFree: num(account.margin_free ?? account.marginFree) },
    risk: { overall: num(risk.overall ?? risk.overall_risk), dailyLoss: num(risk.daily_loss ?? risk.dailyLoss), drawdown: num(risk.drawdown), exposure: num(risk.exposure), positionSize: num(risk.position_size ?? risk.positionSize), aggregateOpenRisk: num(risk.aggregate_open_risk ?? risk.aggregateOpenRisk), protectionState: text(risk.protection_state ?? risk.protectionState), warnings: Array.isArray(risk.warnings) ? risk.warnings.filter((x): x is string => typeof x === "string") : [] },
    positions: mapPositions(root.positions),
    markets,
  };
}

export function mapPositions(input: unknown): Position[] {
  if (!Array.isArray(input)) return [];
  return input.map(obj).filter((p) => typeof p.symbol === "string").map((p) => ({ symbol: String(p.symbol), direction: text(p.direction) ?? undefined, size: num(p.size ?? p.volume), entry: num(p.entry ?? p.entry_price), current: num(p.current ?? p.current_price), pnl: num(p.pnl), stopLoss: num(p.stop_loss ?? p.stopLoss), takeProfit: num(p.take_profit ?? p.takeProfit), status: text(p.status) ?? undefined }));
}

export function mapCandles(input: unknown): Candle[] {
  if (!Array.isArray(input)) return [];
  return input.map(obj).filter((c) => [c.time,c.open,c.high,c.low,c.close].every((v) => typeof v === "number" && Number.isFinite(v))).map((c) => ({ time: c.time as number, open: c.open as number, high: c.high as number, low: c.low as number, close: c.close as number }));
}
