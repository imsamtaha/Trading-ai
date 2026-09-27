export type NavItem = {
  key: "dashboard" | "markets" | "trade" | "signals" | "risk" | "analytics" | "news" | "ai" | "account";
  label: string;
  href: string;
};

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", label: "Dashboard", href: "#dashboard" },
  { key: "markets", label: "Markets", href: "#markets" },
  { key: "trade", label: "Trade", href: "#trade" },
  { key: "signals", label: "Signals", href: "#signals" },
  { key: "risk", label: "Risk", href: "#risk" },
  { key: "analytics", label: "Analytics", href: "#analytics" },
  { key: "news", label: "News", href: "#news" },
  { key: "ai", label: "ATLAS AI", href: "#ai" },
  { key: "account", label: "Account", href: "#account" },
] as const;
