import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import RuntimePage from "@/app/admin/runtime/page";
afterEach(() => vi.unstubAllGlobals());
const state = { instance_id: "old", backend: "ONLINE", demo_execution: false, live_execution: "LOCKED", restart_supported: true };
function reply(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}
it("shows owner status and changes demo permission only after server success", async () => {
  let enabled = false;
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/demo-execution")) enabled = JSON.parse(String(init?.body)).enabled;
    return reply({ ...state, demo_execution: enabled });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<RuntimePage />);
  const toggle = await screen.findByRole("switch");
  await waitFor(() => expect(toggle).toBeEnabled());
  expect(toggle).toHaveAttribute("aria-checked", "false");
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
  expect(fetcher).toHaveBeenCalledWith("/backend/api/runtime/demo-execution", expect.objectContaining({
    method: "POST", credentials: "same-origin", body: '{"enabled":true}',
  }));
});
it("keeps controls disabled when owner authorization fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => reply({}, 403)));
  render(<RuntimePage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Owner");
  expect(screen.getByRole("switch")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Restart backend" })).toBeDisabled();
});
it("reports a failed mutation without claiming execution is enabled", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) =>
    url.endsWith("/demo-execution") ? reply({}, 503) : reply(state)));
  render(<RuntimePage />);
  const toggle = await screen.findByRole("switch");
  await waitFor(() => expect(toggle).toBeEnabled());
  fireEvent.click(toggle);
  expect(await screen.findByRole("alert")).toHaveTextContent("failed");
  expect(toggle).toHaveAttribute("aria-checked", "false");
});
it("disables trading controls during restart until status confirms recovery", async () => {
  let restarting = false;
  const fetcher = vi.fn(async (url: string) => {
    if (url.endsWith("/restart")) { restarting = true; return reply({ status: "RESTARTING" }, 202); }
    if (restarting) return new Promise<Response>(() => {});
    return reply(state);
  });
  vi.stubGlobal("fetch", fetcher);
  render(<RuntimePage />);
  const restart = screen.getByRole("button", { name: "Restart backend" });
  await waitFor(() => expect(restart).toBeEnabled());
  fireEvent.click(restart);
  await waitFor(() => expect(screen.getByRole("switch")).toBeDisabled());
  expect(screen.getByRole("status")).toHaveTextContent("Restart");
});

it("waits for a new backend instance instead of accepting the old online process", async () => {
  let instance = "old";
  const fetcher = vi.fn(async (url: string) => url.endsWith("/restart")
    ? reply({ status: "RESTARTING" }, 202) : reply({ ...state, instance_id: instance }));
  vi.stubGlobal("fetch", fetcher);
  render(<RuntimePage />);
  const restart = screen.getByRole("button", { name: "Restart backend" });
  await waitFor(() => expect(restart).toBeEnabled());
  fireEvent.click(restart);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("waiting"));
  fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
  await waitFor(() => expect(fetcher.mock.calls.filter(([url]) => url.endsWith("/status"))).toHaveLength(2));
  expect(restart).toBeDisabled();
  expect(screen.getByRole("status")).not.toHaveTextContent("successfully");
  instance = "new";
  fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
  await waitFor(() => expect(restart).toBeEnabled());
  expect(screen.getByRole("status")).toHaveTextContent("successfully");
});
