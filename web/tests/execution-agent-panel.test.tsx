import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExecutionAgentPanel } from "@/features/execution/execution-agent-panel";

describe("ExecutionAgentPanel", () => {
  it("renders guard status without owner runtime controls for non-owner users", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "WAITING_CONFIRMATION", last_event: { decision_id: "d1", status: "WAITING_CONFIRMATION" } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ decision_id: "d1", status: "WAITING_CONFIRMATION", reason: null }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Owner access required." }), { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ExecutionAgentPanel />);
    expect(await screen.findByRole("heading", { name: /EXECUTION AGENT/i })).toBeInTheDocument();
    expect((await screen.findAllByText("WAITING_CONFIRMATION")).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getAllByText(/d1/).length).toBeGreaterThan(0));
    expect(screen.queryByRole("button", { name: /Restart Backend/i })).not.toBeInTheDocument();
  });

  it("shows owner runtime controls and toggles demo execution", async () => {
    const runtimeOff = { backend: "ONLINE", demo_execution: false, live_execution: "LOCKED", restart_supported: true };
    const runtimeOn = { ...runtimeOff, demo_execution: true };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "READY", last_event: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(runtimeOff), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(runtimeOn), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ExecutionAgentPanel />);
    expect(await screen.findByText("ONLINE")).toBeInTheDocument();
    expect(screen.getByText("LOCKED")).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /Demo Execution OFF/i });
    fireEvent.click(toggle);
    expect(await screen.findByRole("button", { name: /Demo Execution ON/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Restart Backend/i })).toBeInTheDocument();
  });
});
