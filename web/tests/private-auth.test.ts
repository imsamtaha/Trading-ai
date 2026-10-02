import { describe, expect, it, vi } from "vitest";
import { createBackendSession, safeReturnTo, startGoogleOAuth } from "@/features/auth/session";

describe("private auth session", () => {
  it("exchanges a Supabase access token for an HttpOnly backend cookie", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    await createBackendSession("access-token", fetcher);
    expect(fetcher).toHaveBeenCalledWith("/backend/auth/session", {
      method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" },
      body: JSON.stringify({ access_token: "access-token" }),
    });
  });
  it("returns Google OAuth to the requested internal page", async () => {
    const signInWithOAuth = vi.fn().mockResolvedValue({ data: { url: "https://example.supabase.co/auth/v1/authorize" }, error: null });
    expect(await startGoogleOAuth({ signInWithOAuth }, "https://justai-atlas.online", "https://example.supabase.co", "/admin/runtime")).toBe("https://example.supabase.co/auth/v1/authorize");
    expect(signInWithOAuth).toHaveBeenCalledWith({ provider: "google", options: { redirectTo: "https://justai-atlas.online/login?auth=callback&returnTo=%2Fadmin%2Fruntime" } });
    expect(safeReturnTo("https://evil.example")).toBe("/dashboard");
  });
  it("rejects an OAuth redirect outside the configured Supabase origin", async () => {
    const signInWithOAuth = vi.fn().mockResolvedValue({ data: { url: "https://evil.example/auth/v1/authorize" }, error: null });
    await expect(startGoogleOAuth({ signInWithOAuth }, "https://justai-atlas.online", "https://example.supabase.co")).rejects.toThrow("OAuth");
  });
  it("rejects invalid sessions without redirecting to a dashboard", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("", { status: 401 }));
    await expect(createBackendSession("invalid", fetcher)).rejects.toThrow("session");
  });
});
