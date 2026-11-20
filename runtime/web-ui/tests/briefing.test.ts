import { afterEach, describe, expect, it, vi } from "vitest";
import { getMarketBriefing } from "@/lib/api/briefing";

afterEach(() => vi.unstubAllGlobals());

describe("market briefing", () => {
  it("uses the public briefing endpoint and limits the dashboard to three headlines", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      headlines: [
        { title: "Rates update", source: "CNBC Markets", url: "https://example.com/1" },
        { title: "Gold update", source: "CNBC Markets", url: "https://example.com/2" },
        { title: "Stocks update", source: "CNBC Markets", url: "https://example.com/3" },
        { title: "Fourth item", source: "CNBC Markets", url: "https://example.com/4" },
      ],
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);

    expect(await getMarketBriefing()).toHaveLength(3);
    expect(fetcher.mock.calls[0][0]).toBe("/backend/dashboard/market-briefing");
  });

  it("requests Arabic headlines and preserves their Arabic source and link", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ headlines: [
      { title: "ارتفاع أسعار الذهب", source: "الإخبارية - اقتصاد", url: "https://example.com/ar/gold" },
    ] }), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);

    expect(await getMarketBriefing("ar")).toEqual([
      { title: "ارتفاع أسعار الذهب", source: "الإخبارية - اقتصاد", url: "https://example.com/ar/gold" },
    ]);
    expect(fetcher.mock.calls[0][0]).toBe("/backend/dashboard/market-briefing?language=ar");
  });
});
