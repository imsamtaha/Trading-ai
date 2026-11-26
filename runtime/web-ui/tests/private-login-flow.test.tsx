import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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


it("enables Google for a signed-out user and invokes OAuth when pressed", async () => {
  window.history.replaceState({}, "", "/login?returnTo=%2Fdashboard%23ai");
  const oauth = vi.fn().mockResolvedValue({ data: {}, error: { message: "test provider response" } });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ url: "https://example.supabase.co", anon_key: "public", google_client_id: "" }), { status: 200 })));
  vi.stubGlobal("supabase", { createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }), signInWithOAuth: oauth } }) });
  render(<PrivateLogin />);
  const google = screen.getByRole("button", { name: "Continue with Google" });
  await waitFor(() => expect(google).toBeEnabled());
  fireEvent.click(google);
  await waitFor(() => expect(oauth).toHaveBeenCalledWith({ provider: "google", options: { redirectTo: "http://localhost:3000/login?auth=callback&returnTo=%2Fbackend%2Fapi%2Fme", skipBrowserRedirect: true } }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Google sign-in is unavailable"));
  expect(google).toBeEnabled();
  window.history.replaceState({}, "", "/login");
});


it("reports a failed OAuth callback and removes provider error data from the URL", async () => {
  window.history.replaceState({}, "", "/login?auth=callback&error=server_error&error_code=unexpected_failure&error_description=private-provider-detail&returnTo=%2Fdashboard#error=server_error");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ url: "https://example.supabase.co", anon_key: "public", google_client_id: "" }), { status: 200 })));
  vi.stubGlobal("supabase", { createClient: () => ({ auth: { getSession: async () => ({ data: { session: null } }) } }) });
  render(<PrivateLogin />);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Google sign-in could not be completed"));
  expect(screen.queryByText("private-provider-detail")).not.toBeInTheDocument();
  expect(window.location.search).not.toContain("error");
  expect(window.location.hash).toBe("");
  expect(window.location.search).toContain("returnTo=%2Fdashboard");
  await waitFor(() => expect(screen.getByRole("button", { name: "Email link" })).toBeEnabled());
  window.history.replaceState({}, "", "/login");
});
