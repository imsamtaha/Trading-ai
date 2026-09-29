import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasShell } from "@/components/layout/atlas-shell";

const desktopLabels = ["Dashboard", "Markets", "Trade", "Signals", "Risk", "Analytics", "News", "ATLAS AI", "Account"];
const mobileLabels = ["Dashboard", "Markets", "Trade", "ATLAS AI"];

describe("ATLAS navigation", () => {
  it("keeps desktop destinations and uses four mobile actions", () => {
    render(<AtlasShell><div>content</div></AtlasShell>);
    expect(screen.getByTestId("desktop-sidebar")).toBeInTheDocument();
    const mobile = screen.getByTestId("mobile-nav");
    for (const label of desktopLabels) expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(mobile.querySelectorAll("a")).toHaveLength(4);
    for (const label of mobileLabels) expect(mobile).toHaveTextContent(label);
  });

  it("moves the mobile active color to the pressed section", () => {
    render(<AtlasShell><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    const dashboard = mobile.querySelector('a[href="#dashboard"]')!;
    const ai = mobile.querySelector('a[href="#ai"]')!;
    expect(dashboard).toHaveAttribute("aria-current", "page");
    fireEvent.click(ai);
    expect(ai).toHaveAttribute("aria-current", "page");
    expect(dashboard).not.toHaveAttribute("aria-current", "page");
  });
});
