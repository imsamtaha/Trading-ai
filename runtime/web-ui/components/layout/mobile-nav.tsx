"use client";
import { useState } from "react";

const MOBILE_ITEMS = [
  { key: "markets", label: "الأسواق", href: "#markets" },
  { key: "signals", label: "الإشارات", href: "#signals" },
  { key: "risk", label: "المخاطر", href: "#risk" },
  { key: "news", label: "الأخبار", href: "#news" },
  { key: "ai", label: "ATLAS AI", href: "#ai" },
] as const;

function NavIcon({ kind }: { kind: string }) {
  if (kind === "markets") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17l5-5 4 3 7-9" /><path d="M17 6h3v3" /></svg>;
  if (kind === "signals") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V8m5 11V4m5 15v-7m4 7V9" /></svg>;
  if (kind === "risk") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.7-2.7 8-7 10-4.3-2-7-5.3-7-10V6l7-3z" /></svg>;
  if (kind === "news") return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="8" width="12" height="9" rx="3" /><path d="M9 12h.01M15 12h.01M9 15h6M12 8V5M4 11v3M20 11v3" /></svg>;
}

export function MobileNav() {
  const [active, setActive] = useState("markets");
  return <nav className="atlas-mobile-nav atlas-mobile-nav--five" data-testid="mobile-nav" aria-label="Mobile navigation">
    {MOBILE_ITEMS.map((item) => <a key={item.key} href={item.href} className="atlas-mobile-nav__link"
      aria-current={active === item.key ? "page" : undefined} onClick={() => setActive(item.key)}>
      <span className="atlas-mobile-nav__icon"><NavIcon kind={item.key} /></span><span>{item.label}</span>
    </a>)}
  </nav>;
}
