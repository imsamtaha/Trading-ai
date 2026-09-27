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
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument());
  expect(screen.getByRole("status")).toHaveTextContent("Sign in with Google");
});
