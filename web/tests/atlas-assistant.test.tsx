import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AtlasAssistant } from "@/features/ai/atlas-assistant";

describe("AtlasAssistant", () => {
  it("describes educational scope and limits input", () => {
    render(<AtlasAssistant sendMessage={vi.fn()} />);
    expect(screen.getByText(/does not see your account or live prices/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Ask ATLAS")).toHaveAttribute("maxlength", "1000");
  });
  it("submits a prompt and renders the response", async () => {
    const send = vi.fn().mockResolvedValue({ message: "Risk is within configured limits." });
    render(<AtlasAssistant sendMessage={send} />);
    fireEvent.change(screen.getByLabelText("Ask ATLAS"), { target: { value: "Review risk" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    expect(await screen.findByText("Risk is within configured limits.")).toBeInTheDocument();
  });

  it("shows failure and preserves the prompt", async () => {
    const send = vi.fn().mockRejectedValue(new Error("offline"));
    render(<AtlasAssistant sendMessage={send} />);
    const input = screen.getByLabelText("Ask ATLAS");
    fireEvent.change(input, { target: { value: "Explain signal" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(screen.getByText("Assistant unavailable")).toBeInTheDocument());
    expect(input).toHaveValue("Explain signal");
  });
});
