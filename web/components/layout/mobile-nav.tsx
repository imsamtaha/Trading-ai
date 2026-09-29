"use client";
import { useState } from "react";

const MOBILE_ITEMS = [
  { key: "trade", label: "التداول", href: "#trade" },
  { key: "signals", label: "الإشارات", href: "#signals" },
  { key: "risk", label: "المخاطر", href: "#risk" },
  { key: "news", label: "الأخبار", href: "#news" },
  { key: "ai", label: "ATLAS AI", href: "#ai" },
] as const;

export function MobileNav() {
  const [active, setActive] = useState("trade");
  return <nav className="atlas-mobile-nav atlas-mobile-nav--five" data-testid="mobile-nav" aria-label="Mobile navigation">
    {MOBILE_ITEMS.map((item) => <a key={item.key} href={item.href} className="atlas-mobile-nav__link"
      aria-current={active === item.key ? "page" : undefined} onClick={() => setActive(item.key)}>{item.label}</a>)}
  </nav>;
}