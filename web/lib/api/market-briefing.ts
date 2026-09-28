import { requestJson } from "./client";
export interface MarketBriefing { market_board?: unknown[]; headlines?: unknown[]; status?: string }
export function getMarketBriefing(): Promise<MarketBriefing> { return requestJson<MarketBriefing>("/dashboard/market-briefing"); }
