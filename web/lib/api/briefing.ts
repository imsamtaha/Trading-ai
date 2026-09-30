import { atlasFetch } from "./client";
import { apiPath } from "./config";
export type Headline = { title: string; url: string | null };
export async function getMarketBriefing(): Promise<Headline[]> {
  const raw = await atlasFetch<{ headlines?: unknown }>(apiPath("/api/user/market-briefing"), { cache: "no-store", credentials: "same-origin" });
  if (!Array.isArray(raw?.headlines)) return [];
  return raw.headlines.flatMap((item: unknown) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    const title = row.title_en ?? row.title;
    if (typeof title !== "string" || !title.trim()) return [];
    const url = typeof row.url === "string" && /^https?:\/\//i.test(row.url) ? row.url : null;
    return [{ title, url }];
  });
}
