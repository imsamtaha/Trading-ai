import { afterEach, describe, expect, it, vi } from "vitest";
import { getMarketBriefing } from "@/lib/api/briefing";
afterEach(() => vi.unstubAllGlobals());
describe("market briefing", () => {
  it("maps backend headline titles without inventing data", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({headlines:[{title_en:"Rates update",url:"https://example.com/news"},{}]}),{status:200}));
    vi.stubGlobal("fetch", fetcher);
    expect(await getMarketBriefing()).toEqual([{ title:"Rates update", url:"https://example.com/news", source: null }]);
    expect(fetcher.mock.calls[0][0]).toBe("/backend/api/user/market-briefing");
  });
  it("requests Arabic headlines and preserves their Arabic source and link", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ headlines: [
      { title: "ارتفاع أسعار الذهب", source: "الإخبارية - اقتصاد", url: "https://example.com/ar/gold" },
    ] }), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    expect(await getMarketBriefing("ar")).toEqual([
      { title: "ارتفاع أسعار الذهب", source: "الإخبارية - اقتصاد", url: "https://example.com/ar/gold" },
    ]);
    expect(fetcher.mock.calls[0][0]).toBe("/backend/api/user/market-briefing?language=ar");
  });
});
