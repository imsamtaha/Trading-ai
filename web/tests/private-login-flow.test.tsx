import { render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { PrivateLogin } from "@/features/auth/private-login";

vi.mock("next/script", () => {
  function ScriptMock({ onReady }: { onReady: () => void }) {
    useEffect(() => { onReady(); }, [onReady]);
    return null;
  }
  return { default: ScriptMock };
});
afterEach(() => vi.unstubAllGlobals());

it("offers Supabase Google OAuth when direct Google client ID is absent", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ url: "https://example.supabase.co", anon_key: "public", google_client_id: "" }), { status: 200 })));
  vi.stubGlobal("supabase", { createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }) } }) });
  render(<PrivateLogin />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument(), { timeout: 3000 });
  expect(screen.getByRole("status")).toHaveTextContent("Sign in with Google");
});

it("exchanges the returned OAuth session for the backend cookie", async () => {
  window.history.replaceState({}, "", "/login?code=oauth-code");
  const navigation = vi.spyOn(console, "error").mockImplementation(() => {});
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ url: "https://example.supabase.co", anon_key: "public", google_client_id: "" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  vi.stubGlobal("supabase", { createClient: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "returned-token" } } }) } }) });
  render(<PrivateLogin />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith("/backend/auth/session", expect.objectContaining({
    method: "POST", credentials: "same-origin", body: JSON.stringify({ access_token: "returned-token" }),
  })));
  await waitFor(() => expect(navigation).toHaveBeenCalled());
  expect(String(navigation.mock.calls[0][0])).toContain("Not implemented: navigation");
  navigation.mockRestore();
  window.history.replaceState({}, "", "/login");
});

