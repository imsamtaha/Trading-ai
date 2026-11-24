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

  it("keeps five primary dashboard actions and moves the active color", () => {
    const { container } = render(<DashboardScreen state={DASHBOARD_FIXTURE} />);
    const nav = screen.getByRole("navigation", { name: "التنقل الرئيسي" });
    expect(nav.querySelectorAll("a")).toHaveLength(5);
    for (const label of ["الأسواق", "الإشارات", "المخاطر", "الأخبار", "ATLAS AI"]) expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    expect(container.querySelector('#ai img[alt="ATLAS AI"]')).toBeInTheDocument();
    const trade = screen.getByRole("link", { name: "الأسواق" });
    const atlasAi = screen.getByRole("link", { name: "ATLAS AI" });
    expect(trade).toHaveAttribute("aria-current", "page");
    fireEvent.click(atlasAi);
    expect(atlasAi).toHaveAttribute("aria-current", "page");
    expect(trade).not.toHaveAttribute("aria-current", "page");
  });
});