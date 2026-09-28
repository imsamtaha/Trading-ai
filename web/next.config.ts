import type { NextConfig } from "next";
const origin = process.env.ATLAS_BACKEND_ORIGIN ?? "http://127.0.0.1:8011";
if (!/^https?:\/\/[^/]+$/.test(origin)) throw new Error("ATLAS_BACKEND_ORIGIN must be an origin without a path");
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
      "/health", "/api/user/dashboard", "/api/user/chart-data",
      "/api/user/market-briefing", "/api/user/assistant", "/auth/config", "/auth/session",
      "/auth/callback", "/logout",
    ].map((path) => ({ source: `/backend${path}`, destination: `${origin}${path}` })).concat([
      { source: "/auth/session", destination: `${origin}/auth/session` },
      { source: "/health", destination: `${origin}/health` },
    ]);
  },
};
export default nextConfig;
