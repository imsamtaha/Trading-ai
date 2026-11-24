import { atlasFetch } from "./client";
import { apiPath } from "./config";

export type Headline = { title: string; url: string | null; source?: string | null };
export type MarketQuote = { symbol: string; label: string; category: string; price: number | null; changePct: number | null; quoteTime: string | null; freshness: string; provider: string | null };
export type MarketBriefing = { headlines: Headline[]; quotes: MarketQuote[]; asOf: string | null };

export async function getMarketBriefing(language: "ar" | "en" = "en"): Promise<Headline[]> {
  return (await getMarketDeskBriefing(language)).headlines;
}

export async function getMarketDeskBriefing(language: "ar" | "en" = "en"): Promise<MarketBriefing> {
  const path = apiPath("/dashboard/market-briefing") + (language === "ar" ? "?language=ar" : "");
  const raw = await atlasFetch<{ headlines?: unknown; market_board?: unknown; as_of?: unknown }>(path, { cache: "no-store" });
  const headlines = (Array.isArray(raw?.headlines) ? raw.headlines : []).slice(0, 3).flatMap((item: unknown) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    const title = language === "ar" ? (row.title_ar ?? row.title) : (row.title_en ?? row.title);
    if (typeof title !== "string" || !title.trim()) return [];
    const url = typeof row.url === "string" && /^https?:\/\//i.test(row.url) ? row.url : null;
    const source = typeof row.source === "string" && row.source.trim() ? row.source.trim() : null;
    return [{ title: title.trim(), url, source }];
  });
  const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : null;
  const date = (value: unknown) => typeof value === "string" && Number.isFinite(Date.parse(value)) ? value : null;
  const quotes = (Array.isArray(raw?.market_board) ? raw.market_board : []).flatMap((item: unknown): MarketQuote[] => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    if (typeof row.symbol !== "string" || !row.symbol || typeof row.label !== "string" || typeof row.category !== "string") return [];
    const price = number(row.price);
    const quoteTime = date(row.quote_time);
    const freshness = price === null ? "UNAVAILABLE" : quoteTime && ["FRESH", "DELAYED", "STALE"].includes(String(row.freshness)) ? String(row.freshness) : "UNKNOWN";
    return [{ symbol: row.symbol, label: row.label, category: row.category, price, changePct: number(row.change_percent), quoteTime, freshness, provider: typeof row.provider === "string" ? row.provider : null }];
  });
  return { headlines, quotes, asOf: date(raw?.as_of) };
}
