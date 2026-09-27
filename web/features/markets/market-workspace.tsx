import type { Candle } from "@/lib/api/types";
import { ChartToolbar } from "@/features/chart/chart-toolbar";
import { TradingChart } from "@/features/chart/trading-chart";
import type { TradeLevels } from "@/features/chart/chart-overlays";

export function MarketWorkspace({ candles, symbol, timeframe, levels = {} }: { candles: Candle[]; symbol: string; timeframe: string; levels?: TradeLevels }) {
  return (
    <section className="atlas-card atlas-market-workspace" id="trade">
      <ChartToolbar symbol={symbol} timeframe={timeframe} />
      {candles.length > 0 ? <TradingChart candles={candles} levels={levels} /> : <div className="atlas-chart-empty"><strong>Market data unavailable</strong><span>ATLAS will render candles when the backend returns a valid series.</span></div>}
    </section>
  );
}
