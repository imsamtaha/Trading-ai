import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AtlasAppShell } from "@/app/atlas-app-shell";
afterEach(() => vi.unstubAllGlobals());
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
describe("live dashboard availability", () => {
  it("prompts for sign-in when the private dashboard rejects an anonymous session", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(json(
      path.endsWith("/health") ? { status: "healthy" } : { detail: "Not authenticated" },
      path.endsWith("/health") ? 200 : 401,
    ))));
    render(<AtlasAppShell />);
    expect(await screen.findByText("Sign in to view your ATLAS dashboard")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("Backend degraded")).not.toBeInTheDocument();
    expect(screen.queryByText("Backend offline")).not.toBeInTheDocument();
  });
  it("shows degraded when health succeeds but account telemetry is absent", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(json(
      path.endsWith("/health") ? { status: "healthy" } : path.includes("chart-data") ? { candles: [] } : { mt5: { connected: false } }
    ))));
    render(<AtlasAppShell />);
    await waitFor(() => expect(screen.getByText("Backend degraded")).toBeInTheDocument());
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
  });
  it("clears connected account data after a later failed refresh", async () => {
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/health")) return Promise.resolve(json({status:"healthy"}));
      if (path.includes("/api/user/dashboard")) return Promise.resolve(++reads === 1 ? json({mt5:{connected:true,account:{account_masked:"***1234",balance:500}}}) : json({detail:"down"},503));
      return Promise.resolve(json({candles:[],headlines:[]}));
    }));
    render(<AtlasAppShell refreshMs={1000} />);
    await waitFor(() => expect(screen.getByText("500.00")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Backend degraded")).toBeInTheDocument());
    expect(screen.queryByText("500.00")).not.toBeInTheDocument();
  });
  it("leaves checking when account request never resolves", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.includes("/api/user/dashboard") ? new Promise(() => {}) : Promise.resolve(json(path.endsWith("/health") ? {status:"healthy"} : {candles:[],headlines:[]}))));
    render(<AtlasAppShell timeoutMs={30} />);
    await waitFor(() => expect(screen.getByText("Backend degraded")).toBeInTheDocument());
  });
});
