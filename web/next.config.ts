import type { NextConfig } from "next";
const origin = process.env.ATLAS_BACKEND_ORIGIN ?? "http://127.0.0.1:8011";
if (!/^https?:\/\/[^/]+$/.test(origin)) throw new Error("ATLAS_BACKEND_ORIGIN must be an origin without a path");
const nextConfig: NextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [{ source: "/", has: [{ type: "query" as const, key: "auth", value: "callback" }], destination: "/login", permanent: false }];
  },
  async rewrites() {
    return [
      "/health", "/dashboard/atlas", "/dashboard/chart-data",
      "/dashboard/market-briefing", "/agent/right-hand/chat",
    ].map((path) => ({ source: `/backend${path}`, destination: `${origin}${path}` }));
  },
};
export default nextConfig;
