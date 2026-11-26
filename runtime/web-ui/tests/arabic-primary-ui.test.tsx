import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AccountConnection } from "@/features/trades/account-connection";

describe("Arabic-first ATLAS mobile UI", () => {
  it("renders the MT5 connection card in concise Arabic by default", () => {
    render(<AccountConnection onConnected={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "ربط FxPro MT5" })).toBeInTheDocument();
    expect(screen.getByLabelText("نوع الحساب")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ربط MT5" })).toBeInTheDocument();
  });
});
