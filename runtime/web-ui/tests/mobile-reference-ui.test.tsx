import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PositionsPanel } from "@/features/trades/positions-panel";
import { SignalsPanel } from "@/features/signals/signals-panel";
import { RiskPanel } from "@/features/risk/risk-panel";
import { ActivityPanel } from "@/features/activity/activity-panel";
import { MobileNav } from "@/components/layout/mobile-nav";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("approved mobile reference UI", () => {
  it("uses clean sector headers without the removed side labels", () => {
    render(<><PositionsPanel positions={[]} available={false} /><SignalsPanel signals={[]} available={false} /><RiskPanel risk={DASHBOARD_FIXTURE.risk} /><ActivityPanel available={false} /></>);
    for (const title of ["Open Positions", "Signals", "Risk Controls", "Recent Activity"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.queryByText(/Execution state/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Capital protection/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/System feed/i)).not.toBeInTheDocument();
    expect(document.querySelectorAll(".atlas-reference-header")).toHaveLength(4);
    expect(document.querySelectorAll(".atlas-sector-icon")).toHaveLength(4);
    expect(document.querySelector(".atlas-sector-icon--activity .atlas-sector-logo")).toHaveAttribute("src", "/atlas-logo.webp");
  });

  it("keeps five mobile navigation actions with a direct market destination", () => {
    render(<MobileNav />);
    const nav = screen.getByRole("navigation", { name: "Mobile navigation" });
    expect(nav.querySelectorAll("a")).toHaveLength(5);
    expect(screen.getByRole("link", { name: "الأسواق" })).toHaveAttribute("href", "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/#market");
    expect(nav.querySelectorAll(".atlas-mobile-nav__icon")).toHaveLength(5);
  });

  it("contains the approved mobile reference styling hooks", () => {
    const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
    expect(css).toContain(".atlas-reference-header");
    expect(css).toContain(".atlas-sector-icon");
    expect(css).toContain(".atlas-mobile-reference-card");
    expect(css).toContain(".atlas-mobile-reference-empty");
  });
});
