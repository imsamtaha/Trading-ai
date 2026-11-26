import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasShell } from "@/components/layout/atlas-shell";

const desktopLabels = ["Dashboard", "Markets", "Paper trader", "Training", "Saved workspace", "Discover", "TITAN Council", "Connections", "Account"];
const mobileLabels = ["Dashboard", "Markets", "Paper trader", "TITAN Council", "Connections"];

describe("ATLAS navigation", () => {
  it("keeps desktop destinations and five mobile actions in English mode", () => {
    render(<AtlasShell language="en"><div>content</div></AtlasShell>);
    const mobile = screen.getByTestId("mobile-nav");
    const desktop = screen.getByTestId("desktop-sidebar");
    for (const label of desktopLabels) expect(within(desktop).getByRole("link", { name: label })).toBeInTheDocument();
    expect(mobile.querySelectorAll("a")).toHaveLength(5);
    for (const label of mobileLabels) expect(within(mobile).getByRole("link", { name: label })).toBeInTheDocument();
  });

  it("switches both navigation surfaces to Arabic without changing destinations", () => {
    const { rerender } = render(<AtlasShell language="en"><div>content</div></AtlasShell>);
    rerender(<AtlasShell language="ar"><div>content</div></AtlasShell>);
    const desktop = screen.getByTestId("desktop-sidebar");
    const mobile = screen.getByTestId("mobile-nav");
    expect(within(desktop).getByRole("link", { name: "لوحة التحكم" })).toHaveAttribute("href", "/dashboard");
    expect(within(desktop).getByRole("link", { name: "التداول الورقي" })).toHaveAttribute("href", "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/#trader");
    expect(within(desktop).queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(within(mobile).getByRole("link", { name: "الأسواق" })).toHaveAttribute("href", "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/#market");
    expect(within(mobile).getByRole("link", { name: "مجلس تايتن" })).toHaveAttribute("href", "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/titan/");
    expect(within(mobile).queryByRole("link", { name: "Markets" })).not.toBeInTheDocument();
    expect(mobile).toHaveAttribute("dir", "rtl");
  });
});
