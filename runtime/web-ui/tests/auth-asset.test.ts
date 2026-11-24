import { describe, expect, it } from "vitest";
import { GET } from "@/app/legacy-auth.js/route";
describe("existing Google auth bundle", () => {
  it("serves the repository's original bundle with JavaScript content type", async () => {
    const result = await GET();
    expect(result.status).toBe(200);
    expect(result.headers.get("content-type")).toContain("javascript");
    expect(await result.text()).toContain("google-sign-in");
  });
});
