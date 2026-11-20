import { describe, expect, it } from "vitest";
import config from "@/next.config";

describe("ATLAS backend routing", () => {
  it("never loops API requests back to the frontend port", async () => {
    const routes = await config.rewrites!();
    const afterFiles = Array.isArray(routes) ? routes : routes.afterFiles ?? [];
    const health = afterFiles.find((rule) => rule.source === "/backend/health");
    expect(health?.destination).toBe("http://127.0.0.1:8012/health");
  });
  it("forwards only the requested public and private routes", async () => {
    const routes = await config.rewrites!();
    const afterFiles = Array.isArray(routes) ? routes : routes.afterFiles ?? [];
    for (const source of ["/backend/api/market-preview", "/backend/api/mt5-demo/connect",
      "/backend/api/mt5-demo/connect-real", "/backend/api/mt5-demo/state", "/backend/api/mt5-demo/disconnect",
      "/backend/api/mt5-demo/trading-state", "/backend/api/mt5-demo/activate-trading", "/backend/api/mt5-demo/order",
      "/backend/api/execution-guard/status", "/backend/api/execution-guard/events",
      "/backend/api/me", "/backend/billing/methods", "/backend/billing/plans", "/backend/billing/whish/starter/request", "/backend/billing/whish/admin/:path*"]) {
      expect(afterFiles.some((rule) => rule.source === source || rule.source === "/backend/billing/whish/:path*")).toBe(true);
    }
    expect(afterFiles.some((rule) => rule.source === "/backend/mt5/execute")).toBe(false);
    expect(afterFiles.some((rule) => rule.source.includes("execution-guard/confirm"))).toBe(false);
  });
});
