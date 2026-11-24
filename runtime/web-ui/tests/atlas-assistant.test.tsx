import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AtlasAssistant } from "@/features/ai/atlas-assistant";

describe("AtlasAssistant", () => {
  it("describes Paper-workspace scope and limits input", () => {
    render(<AtlasAssistant sendMessage={vi.fn()} />);
    expect(screen.getByText(/بيئة التداول الورقي/i)).toBeInTheDocument();
    expect(screen.getByLabelText("اسأل ATLAS")).toHaveAttribute("maxlength", "1000");
  });

  it("submits a prompt and renders the response", async () => {
    const send = vi.fn().mockResolvedValue({ message: "Risk is within configured limits." });
    render(<AtlasAssistant sendMessage={send} />);
    fireEvent.change(screen.getByLabelText("اسأل ATLAS"), { target: { value: "Review risk" } });
    fireEvent.click(screen.getByRole("button", { name: "إرسال" }));
    expect(screen.getByRole("button", { name: "جارٍ الإرسال…" })).toBeDisabled();
    expect(await screen.findByText("Risk is within configured limits.")).toBeInTheDocument();
    expect(screen.getByLabelText("اسأل ATLAS")).toHaveValue("");
  });

  it("keeps ATLAS AI inside the assistant heading in both languages", () => {
    const { rerender } = render(<AtlasAssistant sendMessage={vi.fn()} language="ar" />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("ATLAS AI");
    rerender(<AtlasAssistant sendMessage={vi.fn()} language="en" />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("ATLAS AI");
  });

  it("shows a sign-in action while ATLAS AI is locked", () => {
    render(<AtlasAssistant sendMessage={vi.fn()} enabled={false} lockedHref="/login?returnTo=%2Fdashboard" />);
    expect(screen.getByLabelText("اسأل ATLAS")).toBeDisabled();
    expect(screen.getByRole("link", { name: "تسجيل الدخول لتفعيل ATLAS AI" })).toHaveAttribute("href", "/login?returnTo=%2Fdashboard");
  });

  it("shows failure and preserves the prompt", async () => {
    const send = vi.fn().mockRejectedValue(new Error("offline"));
    render(<AtlasAssistant sendMessage={send} />);
    const input = screen.getByLabelText("اسأل ATLAS");
    fireEvent.change(input, { target: { value: "Explain signal" } });
    fireEvent.click(screen.getByRole("button", { name: "إرسال" }));
    await waitFor(() => expect(screen.getByText("المساعد غير متاح")).toBeInTheDocument());
    expect(input).toHaveValue("Explain signal");
  });
});
