import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SubscriptionFlow } from "@/features/billing/subscription-flow";
afterEach(() => vi.unstubAllGlobals());

it("requests manual Whish review under the signed-in identity without unlocking access", async () => {
  const fetch = vi.fn((url: string) => Promise.resolve(new Response(JSON.stringify(
    url.includes("/api/me") ? { user: { email: "buyer@example.com" } } :
    url.includes("/billing/plans") ? { plans: [{ id: "starter", name: "Starter", monthly_price: 99, features: [] }] } :
    { reference: "ATLAS-123", status: "PENDING_REVIEW", access_granted: false }
  ), { status: 200 })));
  vi.stubGlobal("fetch", fetch);
  render(<SubscriptionFlow />);
  fireEvent.click(await screen.findByRole("button", { name: "Request Starter" }));
  await waitFor(() => expect(screen.getByText(/ATLAS-123/)).toBeInTheDocument());
  expect(fetch.mock.calls.at(-1)?.[0]).toContain("/backend/billing/whish/starter/request");
  expect(JSON.parse(fetch.mock.calls.at(-1)?.[1]?.body)).toEqual({ email: "buyer@example.com" });
  expect(screen.getByText(/pending owner review/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Email payment proof to owner" })).toHaveAttribute("href", expect.stringContaining("mailto:imsamtaha.ai@gmail.com"));
});
