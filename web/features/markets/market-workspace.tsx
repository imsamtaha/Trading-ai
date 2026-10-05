"use client";
import { useEffect, useState } from "react";
import type { ReactElement } from "react";
import { ChartToolbar, TIMEFRAMES } from "../chart/chart-toolbar";
import { TradingChart } from "../chart/trading-chart";
import { getCandles } from "../../lib/api/market";
import type { Candle } from "../../lib/api/types";
export function MarketWorkspace(): ReactElement {
  const [symbol, setSymbol] = useState("EURUSD"); const [timeframe, setTimeframe] = useState<typeof TIMEFRAMES[number]>("1h"); const [candles, setCandles] = useState<Candle[]>([]); const [failed, setFailed] = useState(false);
  useEffect(() => { let live = true; setCandles([]); setFailed(false); getCandles(symbol, timeframe, 150).then(data => { if (live) setCandles(data); }).catch(() => { if (live) setFailed(true); }); return () => { live = false; }; }, [symbol, timeframe]);
  return <section className="atlas-card atlas-market-workspace"><div className="atlas-section-heading"><div><p className="atlas-eyebrow">MARKET WORKSPACE</p><h2>Price action</h2></div><span className="atlas-pill atlas-pill--muted">READ ONLY</span></div><ChartToolbar symbol={symbol} timeframe={timeframe} onSymbol={setSymbol} onTimeframe={value => setTimeframe(value)} />{failed ? <div role="status" className="atlas-chart-empty">Market data is unavailable. Check the backend connection and try again.</div> : <TradingChart candles={candles} symbol={symbol} timeframe={timeframe} />}</section>;
}
