import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasShell } from "@/components/layout/atlas-shell";

const desktopLabels = ["Dashboard", "Markets", "Trade", "Signals", "Risk", "Analytics", "News", "ATLAS AI", "Account"];
const mobileLabels = ["Markets", "Signals", "Risk", "News", "ATLAS AI"];

describe("ATLAS navigation", () => {
  it("keeps desktop destinations and five mobile actions in English mode", () => {
    render(<AtlasShell language="en"><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    const desktop = screen.getByTestId("desktop-sidebar");
    for (const label of desktopLabels) expect(within(desktop).getByRole("link", { name: label })).toBeInTheDocument();
    expect(mobile.querySelectorAll("a")).toHaveLength(5);
    for (const label of mobileLabels) expect(within(mobile).getByRole("link", { name: label })).toBeInTheDocument();
  });

  it("starts on Markets and moves the active indicator to the selected section", () => {
    render(<AtlasShell language="en"><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    const markets = within(mobile).getByRole("link", { name: "Markets" });
    const news = within(mobile).getByRole("link", { name: "News" });
    expect(markets).toHaveAttribute("aria-current", "page");
    fireEvent.click(news);
    expect(news).toHaveAttribute("aria-current", "page");
    expect(markets).not.toHaveAttribute("aria-current", "page");
    expect(mobile.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
  });

  it("switches both navigation surfaces to Arabic without changing destinations", () => {
    const { rerender } = render(<AtlasShell language="en"><div>content</div></AtlasShell>);
    rerender(<AtlasShell language="ar"><div>content</div></AtlasShell>);
    const desktop = screen.getByTestId("desktop-sidebar");
    const mobile = screen.getByTestId("mobile-nav");
    expect(within(desktop).getByRole("link", { name: "لوحة التحكم" })).toHaveAttribute("href", "#dashboard");
    expect(within(desktop).getByRole("link", { name: "التداول" })).toHaveAttribute("href", "#trade");
    expect(within(desktop).queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(within(mobile).getByRole("link", { name: "الأسواق" })).toHaveAttribute("href", "#markets");
    expect(within(mobile).getByRole("link", { name: "الأخبار" })).toHaveAttribute("href", "#news");
    expect(within(mobile).queryByRole("link", { name: "Markets" })).not.toBeInTheDocument();
    expect(mobile).toHaveAttribute("dir", "rtl");
  });
});
