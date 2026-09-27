import { afterEach, describe, expect, it, vi } from "vitest";
import { getMarketBriefing } from "@/lib/api/briefing";
afterEach(() => vi.unstubAllGlobals());
describe("market briefing", () => {
  it("maps backend headline titles without inventing data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({headlines:[{title_en:"Rates update",url:"https://example.com/news"},{}]}),{status:200})));
    expect(await getMarketBriefing()).toEqual([{ title:"Rates update", url:"https://example.com/news" }]);
  });
});
