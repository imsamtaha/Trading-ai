import { atlasFetch } from "./client";
import { apiPath } from "./config";

export type Headline = { title: string; url: string | null; source?: string | null };

export async function getMarketBriefing(language: "ar" | "en" = "en"): Promise<Headline[]> {
  const path = apiPath("/dashboard/market-briefing") + (language === "ar" ? "?language=ar" : "");
  const raw = await atlasFetch<{ headlines?: unknown }>(path, { cache: "no-store" });
  if (!Array.isArray(raw?.headlines)) return [];
  return raw.headlines.slice(0, 3).flatMap((item: unknown) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    const title = language === "ar" ? (row.title_ar ?? row.title) : (row.title_en ?? row.title);
    if (typeof title !== "string" || !title.trim()) return [];
    const url = typeof row.url === "string" && /^https?:\/\//i.test(row.url) ? row.url : null;
    const source = typeof row.source === "string" && row.source.trim() ? row.source.trim() : null;
    return [{ title: title.trim(), url, source }];
  });
}
