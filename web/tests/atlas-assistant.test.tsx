import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AtlasAssistant } from "../features/ai/atlas-assistant";
vi.mock("../lib/api/agent", () => ({ sendAgentMessage: vi.fn() }));
import { sendAgentMessage } from "../lib/api/agent";
const mockedSend = vi.mocked(sendAgentMessage);
beforeEach(() => vi.clearAllMocks());
describe("AtlasAssistant", () => {
  it("submits prompt and shows response", async () => { mockedSend.mockResolvedValue({ message: "Review the market structure." }); render(<AtlasAssistant />); fireEvent.change(screen.getByLabelText("Message ATLAS AI"), { target: { value: "Review EURUSD" } }); fireEvent.click(screen.getAllByRole("button", { name: "Send" }).at(-1)!); expect(screen.getByText("Thinking…")).toBeInTheDocument(); await waitFor(() => expect(screen.getByText("Review the market structure.")).toBeInTheDocument()); expect(mockedSend).toHaveBeenCalledWith(expect.objectContaining({ request: "Review EURUSD" })); });
  it("preserves prompt and reports failure", async () => { mockedSend.mockRejectedValue(new Error("offline")); render(<AtlasAssistant />); const input = screen.getByLabelText("Message ATLAS AI"); fireEvent.change(input, { target: { value: "Check gold" } }); fireEvent.click(screen.getAllByRole("button", { name: "Send" }).at(-1)!); await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument()); expect(input).toHaveValue("Check gold"); });
});
