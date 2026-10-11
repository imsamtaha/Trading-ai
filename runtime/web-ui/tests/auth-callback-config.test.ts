import { describe, expect, it } from "vitest";
import config from "@/next.config";
describe("Google callback routing", () => {
  it("routes only the legacy root callback to the page running the existing auth bundle", async () => {
    const rules = await config.redirects!();
    expect(rules).toContainEqual(expect.objectContaining({
      source: "/", destination: "/login",
      has: [{ type: "query", key: "auth", value: "callback" }],
    }));
  });
});
