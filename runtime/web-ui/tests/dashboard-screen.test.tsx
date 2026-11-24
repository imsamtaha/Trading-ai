import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("DashboardScreen", () => {
  it("renders account and market telemetry", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} briefingAvailable headlines={[{ title: "Rates update", url: "https://example.com/news" }]} />);
    expect(screen.getByRole("heading", { level: 1, name: "ATLAS" })).toBeInTheDocument();
    expect(screen.queryByText(/ATLAS INTELLIGENCE/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Trading Intelligence · Paper Lab/i)).not.toBeInTheDocument();
    expect(screen.getByText("10,000.00")).toBeInTheDocument();
    expect(screen.getByText("10,248.42")).toBeInTheDocument();
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
    expect(screen.getAllByText("XAUUSD").length).toBeGreaterThan(0);
    expect(document.getElementById("analytics")).toBeInTheDocument();
    expect(document.getElementById("news")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rates update" })).toHaveAttribute("href", "https://example.com/news");
  });

  it("shows an Arabic headline with its Arabic source and original link", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} language="ar" briefingAvailable headlines={[
      { title: "أسواق المال اليوم", source: "الإخبارية - أسواق", url: "https://example.com/ar/markets" },
    ]} />);
    expect(screen.getByRole("link", { name: "أسواق المال اليوم" })).toHaveAttribute("href", "https://example.com/ar/markets");
    expect(screen.getByText("المصدر: الإخبارية - أسواق")).toBeInTheDocument();
  });

  it("shows chart levels only for the selected matching position", () => {
    const { rerender } = render(<DashboardScreen state={DASHBOARD_FIXTURE} symbol="BTCUSDT" />);
    expect(screen.getByText("Entry 66,420")).toBeInTheDocument();
    rerender(<DashboardScreen state={DASHBOARD_FIXTURE} symbol="XAUUSD" />);
    expect(screen.queryByText("Entry 66,420")).not.toBeInTheDocument();
  });

  it("renders explicit offline placeholders", () => {
    render(<DashboardScreen state={{ ...DASHBOARD_FIXTURE, connection: "offline", account: { ...DASHBOARD_FIXTURE.account, balance: null } }} />);
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
    expect(screen.getByText("Positions unavailable")).toBeInTheDocument();
    expect(screen.getByText("Signals unavailable")).toBeInTheDocument();
  });
});

it("labels each Arabic dashboard sector with an AGENT badge", () => {
  render(<DashboardScreen state={DASHBOARD_FIXTURE} language="ar" />);
  expect(screen.getAllByText("AGENT")).toHaveLength(9);
  for (const title of ["السوق", "الصفقات المفتوحة", "الإشارات", "ضوابط المخاطر", "النشاط الأخير", "الأداء", "أخبار السوق", "المساعد الذكي", "وكيل التنفيذ"]) {
    const heading = screen.getAllByRole("heading").find((item) => item.textContent?.includes(title));
    expect(heading).toBeDefined();
    expect(heading?.closest("section,div")?.textContent).toContain("AGENT");
  }
});

it("uses English AGENT titles in English mode", () => {
  render(<DashboardScreen state={DASHBOARD_FIXTURE} language="en" />);
  for (const title of ["Market", "Open Positions", "Signals", "Risk Controls", "Recent Activity", "Performance", "Market News", "AI Assistant", "Execution Agent"]) {
    expect(screen.getAllByRole("heading").some((item) => item.textContent?.includes(title))).toBe(true);
  }
});

it("styles dashboard headings as orange 3D blocks and paragraphs yellow", () => {
  const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
  expect(css).toContain(".atlas-dashboard .atlas-card h2");
  expect(css).toContain(".atlas-dashboard .atlas-card p");
  expect(css).toContain("color: #ffd84d");
});

it("shows OWNER in the account status when the signed-in role is owner", () => {
  render(<DashboardScreen state={{ ...DASHBOARD_FIXTURE, userRole: "OWNER", account: { ...DASHBOARD_FIXTURE.account, mode: null } }} />);
  expect(screen.getByText("OWNER")).toBeInTheDocument();
  expect(screen.queryByText("زائر")).not.toBeInTheDocument();
});

it("styles headings as dark 3D boxes with black edge and orange text", () => {
  const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
  expect(css).toContain("background: linear-gradient(145deg, #2a2a2a");
  expect(css).toContain("border: 1px solid #050505");
  expect(css).toContain("color: var(--atlas-orange)");
  const badgeCss = css.slice(css.indexOf(".atlas-agent-badge"), css.indexOf(".atlas-sector-title"));
  expect(badgeCss).toContain("border: 1px solid #050505");
  expect(badgeCss).toContain("background: linear-gradient(145deg, #242424");
  expect(badgeCss).toContain("color: var(--atlas-orange)");
});
