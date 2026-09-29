"use client";

import { useState } from "react";
import { NAV_ITEMS } from "@/lib/navigation";

const MOBILE_KEYS = new Set(["dashboard", "markets", "trade", "ai"]);
const MOBILE_ITEMS = NAV_ITEMS.filter((item) => MOBILE_KEYS.has(item.key));

export function MobileNav() {
  const [activeKey, setActiveKey] = useState("dashboard");
  return (
    <nav className="atlas-mobile-nav" data-testid="mobile-nav" aria-label="Mobile navigation">
      {MOBILE_ITEMS.map((item) => (
        <a
          key={item.key}
          href={item.href}
          className="atlas-mobile-nav__link"
          aria-current={activeKey === item.key ? "page" : undefined}
          onClick={() => setActiveKey(item.key)}
        >
          {item.label}
        </a>
      ))}
    </nav>
  );
}
