import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
describe("browser-facing deployment config", () => {
  it("uses only public backend routing in the example", () => {
    const example = readFileSync(resolve(process.cwd(), ".env.example"), "utf8");
    expect(example).toContain("ATLAS_BACKEND_ORIGIN=");
    expect(example).not.toMatch(/NEXT_PUBLIC_.*(?:SECRET|PASSWORD|TOKEN|KEY)/i);
  });
});
