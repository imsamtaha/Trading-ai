import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
describe("browser-facing deployment config", () => {
  it("uses only public backend routing in the example", () => {
    const example = readFileSync(resolve(process.cwd(), ".env.example"), "utf8");
    expect(example).toContain("ATLAS_BACKEND_ORIGIN=");
    expect(example).not.toMatch(/NEXT_PUBLIC_.*(?:SECRET|PASSWORD|TOKEN|KEY)/i);
    const config = readFileSync(resolve(process.cwd(), "next.config.ts"), "utf8");
    expect(config).toContain('"/api/user/dashboard"');
    expect(config).toContain('"/api/user/chart-data"');
    expect(config).toContain('"/api/user/market-briefing"');
    expect(config).toContain('"/api/user/assistant"');
    expect(config).toContain('"/auth/session"');
    expect(config).not.toContain('"/dashboard/atlas"');
  });
});
