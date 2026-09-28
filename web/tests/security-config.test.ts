import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
describe("browser configuration security contract", () => {
  it("publishes only the non-secret backend origin setting", () => {
    const example = readFileSync(".env.example", "utf8");
    expect(example).toContain("NEXT_PUBLIC_ATLAS_API_BASE_URL");
    expect(example).not.toMatch(/OPENAI_API_KEY|MT5_PASSWORD|ATLAS_LIVE_AUTH|EXECUTION_TOKEN|AUTHORIZATION/i);
  });
});
