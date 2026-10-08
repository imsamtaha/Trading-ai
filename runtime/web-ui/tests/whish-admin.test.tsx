import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import WhishAdminPage from "@/app/admin/whish/page";
afterEach(() => vi.unstubAllGlobals());

it("requires manual payment verification before admin approval", async () => {
  const fetch = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>((url: string) => Promise.resolve(new Response(JSON.stringify(
    url.endsWith("/requests") ? { requests: [{ reference: "ATLAS-ABC", email: "buyer@example.com", plan_id: "starter", amount_usd: 99, created_at: "2026-09-28" }] } :
    { status: "APPROVED" }
  ), { status: 200 })));
  vi.stubGlobal("fetch", fetch);
  render(<WhishAdminPage />);
  const approve = await screen.findByRole("button", { name: "Approve subscription" });
  expect(approve).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox", { name: /verified the Whish transfer/i }));
  fireEvent.click(approve);
  await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => url.includes("/approve") && init?.method === "POST")).toBe(true));
});
