import type { ReactElement } from "react";
export const TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"] as const;
export function ChartToolbar({ symbol, timeframe, onSymbol, onTimeframe }: { symbol: string; timeframe: string; onSymbol: (value: string) => void; onTimeframe: (value: typeof TIMEFRAMES[number]) => void }): ReactElement {
  return <div className="atlas-chart-toolbar"><label>Symbol <select aria-label="Symbol" value={symbol} onChange={e => onSymbol(e.target.value)}>{["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"].map(s => <option key={s}>{s}</option>)}</select></label><div role="group" aria-label="Timeframe">{TIMEFRAMES.map(tf => <button key={tf} type="button" aria-pressed={timeframe === tf} onClick={() => onTimeframe(tf)}>{tf}</button>)}</div></div>;
}
