import type { NextConfig } from "next";
const origin = process.env.ATLAS_BACKEND_ORIGIN ?? "http://127.0.0.1:8012";
if (!/^https?:\/\/[^/]+$/.test(origin)) throw new Error("ATLAS_BACKEND_ORIGIN must be an origin without a path");
if (origin === "http://127.0.0.1:8011") throw new Error("ATLAS_BACKEND_ORIGIN cannot point to the frontend port");
const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.ATLAS_BUILD_DIR || ".next",
  async redirects() {
    return [
      { source: "/", has: [{ type: "query" as const, key: "auth", value: "callback" }], destination: "/login", permanent: false },
      { source: "/app/dashboard", destination: "/dashboard", permanent: false },
    ];
  },
  async rewrites() {
    return [
      "/health", "/api/market-preview", "/api/user/dashboard", "/api/user/chart-data",
      "/api/me", "/api/user/market-briefing", "/api/user/assistant",
      "/api/mt5-demo/connect", "/api/mt5-demo/connect-real", "/api/mt5-demo/state", "/api/mt5-demo/disconnect",
      "/api/mt5-demo/trading-state", "/api/mt5-demo/activate-trading", "/api/mt5-demo/order",
      "/billing/methods", "/billing/plans", "/billing/whish/starter/request",
      "/billing/whish/pro/request", "/billing/whish/elite/request",
      "/auth/config", "/auth/session",
      "/auth/callback", "/logout",
    ].map((path) => ({ source: `/backend${path}`, destination: `${origin}${path}` })).concat([
      { source: "/backend/billing/whish/admin/:path*", destination: `${origin}/billing/whish/admin/:path*` },
      { source: "/auth/session", destination: `${origin}/auth/session` },
      { source: "/health", destination: `${origin}/health` },
    ]);
  },
};
export default nextConfig;
