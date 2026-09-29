import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AccountConnection } from "@/features/trades/account-connection";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("Arabic-first ATLAS mobile UI", () => {
  it("renders the MT5 connection card in concise Arabic by default", () => {
    render(<AccountConnection onConnected={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "ربط FxPro MT5" })).toBeInTheDocument();
    expect(screen.getByLabelText("نوع الحساب")).toBeInTheDocument();
    expect(screen.getByLabelText("رقم MT5")).toBeInTheDocument();
    expect(screen.getByLabelText("كلمة المرور")).toBeInTheDocument();
    expect(screen.getByLabelText("الخادم")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ربط MT5" })).toBeInTheDocument();
  });

  it("uses concise Arabic dashboard navigation", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} />);
    for (const label of ["الرئيسية", "الأسواق", "التداول", "الإشارات", "المخاطر", "التحليل"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
