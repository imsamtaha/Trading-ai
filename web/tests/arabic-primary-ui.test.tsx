import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AccountConnection } from "@/features/trades/account-connection";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("Arabic-first ATLAS mobile UI", () => {
  it("renders the MT5 connection card in concise Arabic by default", () => {
    render(<AccountConnection onConnected={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "ربط FxPro MT5" })).toBeInTheDocument();
    expect(screen.getByLabelText("نوع الحساب")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ربط MT5" })).toBeInTheDocument();
  });

  it("moves the active color with the selected dashboard button", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} />);
    const home = screen.getByRole("link", { name: "الرئيسية" });
    const markets = screen.getByRole("link", { name: "الأسواق" });
    expect(home).toHaveAttribute("aria-current", "page");
    fireEvent.click(markets);
    expect(markets).toHaveAttribute("aria-current", "page");
    expect(home).not.toHaveAttribute("aria-current", "page");
  });
});