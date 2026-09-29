import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ManualTrading } from "@/features/trades/manual-trading";
afterEach(() => vi.unstubAllGlobals());

it("submits a Demo order only after a separate review and confirmation", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ connected: true, active: true, account_type: "DEMO", account_masked: "***1234" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "FILLED", ticket: 42 }), { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  render(<ManualTrading />);
  await screen.findByText(/Demo account.*1234/i);
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "EURUSD" } });
  fireEvent.change(screen.getByLabelText("Volume"), { target: { value: "0.01" } });
  fireEvent.change(screen.getByLabelText("Stop loss"), { target: { value: "1.19" } });
  fireEvent.change(screen.getByLabelText("Take profit"), { target: { value: "1.21" } });
  fireEvent.click(screen.getByRole("button", { name: "Review order" }));
  expect(fetch).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Confirm Demo order" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(fetch.mock.calls[1][0]).toContain("/api/mt5-demo/order");
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toMatchObject({ account_type: "DEMO", confirmed: true, symbol: "EURUSD" });
  expect(JSON.parse(fetch.mock.calls[1][1].body).request_id).toMatch(/^[0-9a-f-]{36}$/);
  expect(await screen.findByText(/ticket 42/i)).toBeInTheDocument();
});

it("requires explicit activation for a Live account and does not order on connection", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ connected: true, active: false, server_enabled: true, account_type: "REAL", account_masked: "***7777" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ connected: true, active: true, account_type: "REAL", account_masked: "***7777" }), { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  render(<ManualTrading />);
  await screen.findByText(/Live account.*7777/i);
  expect(screen.queryByRole("button", { name: "Review order" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Activate Live trading" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(fetch.mock.calls[1][0]).toContain("/api/mt5-demo/activate-trading");
  expect(fetch.mock.calls.map((call) => call[0])).not.toContain("/backend/api/mt5-demo/order");
});

it("shows an unavailable state when trading status cannot be read", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("offline", { status: 503 })));
  render(<ManualTrading />);
  expect(await screen.findByRole("status")).toHaveTextContent("Trading state unavailable");
});

it("keeps the trading section visible when MT5 is disconnected", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ connected: false, active: false, account_type: null }), { status: 200 })));
  const { container } = render(<ManualTrading />);
  await waitFor(() => expect(container.querySelector("#trade")).toBeInTheDocument());
  expect(container.querySelector("#trade")).toHaveClass("atlas-feature-3d");
  expect(screen.getByText(/Connect MT5/i)).toBeInTheDocument();
});