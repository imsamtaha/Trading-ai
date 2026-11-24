import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AccountConnection } from "@/features/trades/account-connection";
afterEach(() => vi.unstubAllGlobals());

it("connects the selected MT5 account without submitting an order", async () => {
  const fetch = vi.fn().mockImplementation((url: string) => Promise.resolve(new Response(JSON.stringify(
    url.includes("/api/me") ? { user: { role: "OWNER" } } : { connected: true, account_type: "REAL", real_money_execution_enabled: false }
  ), { status: 200 })));
  vi.stubGlobal("fetch", fetch);
  const connected = vi.fn();
  render(<AccountConnection language="en" onConnected={connected} />);
  fireEvent.change(screen.getByLabelText("Account type"), { target: { value: "REAL" } });
  fireEvent.change(screen.getByLabelText("MT5 login"), { target: { value: "12345678" } });
  fireEvent.change(screen.getByLabelText("MT5 password"), { target: { value: "secret" } });
  fireEvent.change(screen.getByLabelText("MT5 server"), { target: { value: "FxPro" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Connect MT5" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Connect MT5" }));
  await waitFor(() => expect(connected).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[1][0]).toContain("/api/mt5-demo/connect-real");
  expect(fetch.mock.calls[1][1].credentials).toBe("same-origin");
  expect(screen.getByLabelText("MT5 password")).toHaveValue("");
  expect(screen.getByRole("status")).toHaveTextContent("connected");
  expect(fetch).toHaveBeenCalledTimes(2);
});
