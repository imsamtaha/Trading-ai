import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasShell } from "@/components/layout/atlas-shell";

const desktopLabels = ["Dashboard", "Markets", "Trade", "Signals", "Risk", "Analytics", "News", "ATLAS AI", "Account"];
const mobileLabels = ["التداول", "الإشارات", "المخاطر", "الأخبار", "ATLAS AI"];

describe("ATLAS navigation", () => {
  it("keeps desktop destinations and uses five mobile actions", () => {
    render(<AtlasShell><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    for (const label of desktopLabels) expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(mobile.querySelectorAll("a")).toHaveLength(5);
    for (const label of mobileLabels) expect(mobile).toHaveTextContent(label);
  });

  it("starts on ATLAS AI and moves the active color to the pressed section", () => {
    render(<AtlasShell><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    const ai = mobile.querySelector('a[href="#ai"]')!;
    const news = mobile.querySelector('a[href="#news"]')!;
    expect(ai).toHaveAttribute("aria-current", "page");
    fireEvent.click(news);
    expect(news).toHaveAttribute("aria-current", "page");
    expect(ai).not.toHaveAttribute("aria-current", "page");
  });
});
