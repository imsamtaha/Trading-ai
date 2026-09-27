const timeframes = ["5m", "15m", "30m", "1h", "4h", "1d"] as const;

export function ChartToolbar({ symbol, timeframe }: { symbol: string; timeframe: string }) {
  return (
    <div className="atlas-chart-toolbar">
      <div><span className="atlas-card-label">Instrument</span><strong>{symbol}</strong></div>
      <div className="atlas-timeframes" aria-label="Timeframes">
        {timeframes.map((tf) => <button key={tf} type="button" aria-pressed={tf === timeframe}>{tf}</button>)}
      </div>
    </div>
  );
}
