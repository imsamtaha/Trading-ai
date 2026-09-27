const timeframes = ["5m", "15m", "30m", "1h", "4h", "1d"] as const;
const symbols = ["XAUUSD", "XAGUSD", "GAS", "EURUSD", "XRPUSDT", "SOLUSDT"] as const;
export function ChartToolbar({ symbol, timeframe, onChange }: { symbol: string; timeframe: string; onChange?: (symbol: string, timeframe: string) => void }) {
  return <div className="atlas-chart-toolbar">
    <div><label className="atlas-card-label" htmlFor="atlas-chart-symbol">Instrument</label>
      {onChange ? <select id="atlas-chart-symbol" aria-label="Instrument" value={symbol} onChange={(e) => onChange(e.target.value, timeframe)}>{symbols.map((s) => <option key={s}>{s}</option>)}</select> : <strong>{symbol}</strong>}
    </div>
    <div className="atlas-timeframes" aria-label="Timeframes">
      {timeframes.map((tf) => <button key={tf} type="button" aria-pressed={tf === timeframe} onClick={() => onChange?.(symbol, tf)}>{tf}</button>)}
    </div>
  </div>;
}
