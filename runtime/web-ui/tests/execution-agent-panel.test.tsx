import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExecutionAgentPanel } from "@/features/execution/execution-agent-panel";

describe("ExecutionAgentPanel", () => {
  it("renders guard status and audit events without live execution controls or redundant guard copy", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "WAITING_CONFIRMATION", last_event: { decision_id: "d1", status: "WAITING_CONFIRMATION" } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ decision_id: "d1", status: "WAITING_CONFIRMATION", reason: null }]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ExecutionAgentPanel />);
    expect(await screen.findByRole("heading", { name: /EXECUTION AGENT/i })).toBeInTheDocument();
    expect(screen.queryByText(/^Execution Guard$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Execution Guard unavailable/i)).not.toBeInTheDocument();
    expect((await screen.findAllByText("WAITING_CONFIRMATION")).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getAllByText(/d1/).length).toBeGreaterThan(0));
    expect(screen.queryByRole("button", { name: /confirm|execute|تنفيذ|تأكيد/i })).not.toBeInTheDocument();
  });
  it("shows execution terms in Arabic when Arabic is selected", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "READY" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ decision_id: "d2", status: "BLOCKED", reason: "Demo execution is disabled." }]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ExecutionAgentPanel language="ar" />);
    expect(screen.getByRole("heading", { name: /وكيل التنفيذ/ })).toBeInTheDocument();
    expect(await screen.findByText("حالة الحماية:")).toBeInTheDocument();
    expect(await screen.findByText("جاهز")).toBeInTheDocument();
    expect(await screen.findByText("محظور")).toBeInTheDocument();
    expect(screen.getByText(/تنفيذ الصفقات التجريبية معطّل/)).toBeInTheDocument();
    expect(screen.queryByText(/Demo decisions may auto-execute/)).not.toBeInTheDocument();
  });
});
