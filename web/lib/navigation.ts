export type Destination =
  | "dashboard"
  | "markets"
  | "trade"
  | "signals"
  | "risk"
  | "analytics"
  | "news"
  | "ai"
  | "account";

export type NavItem = {
  id: Destination;
  label: string;
  href: string;
};

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", href: "/" },
  { id: "markets", label: "Markets", href: "/markets/" },
  { id: "trade", label: "Trade", href: "/trade/" },
  { id: "signals", label: "Signals", href: "/signals/" },
  { id: "risk", label: "Risk", href: "/risk/" },
  { id: "analytics", label: "Analytics", href: "/analytics/" },
  { id: "news", label: "News", href: "/news/" },
  { id: "ai", label: "ATLAS AI", href: "/ai/" },
  { id: "account", label: "Account", href: "/account/" },
] as const satisfies readonly NavItem[];
