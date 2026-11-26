"use client";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/navigation";

const mobileKeys = new Set<string>(["dashboard", "markets", "trade", "council", "connect"]);
const MOBILE_ITEMS = NAV_ITEMS.filter(item => mobileKeys.has(item.key));

function NavIcon({ kind }: { kind: string }) {
  if (kind === "markets") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17l5-5 4 3 7-9" /><path d="M17 6h3v3" /></svg>;
  if (kind === "trade") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V8m5 11V4m5 15v-7m4 7V9" /></svg>;
  if (kind === "council") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.7-2.7 8-7 10-4.3-2-7-5.3-7-10V6l7-3z" /></svg>;
  if (kind === "dashboard") return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="8" width="12" height="9" rx="3" /><path d="M9 12h.01M15 12h.01M9 15h6M12 8V5M4 11v3M20 11v3" /></svg>;
}

export function MobileNav({ language = "ar" }: { language?: "ar" | "en" }) {
  const pathname = usePathname();
  return <nav className="atlas-mobile-nav atlas-mobile-nav--five" data-testid="mobile-nav" aria-label="Mobile navigation" dir={language === "ar" ? "rtl" : "ltr"}>
    {MOBILE_ITEMS.map((item) => <a key={item.key} href={item.href} className="atlas-mobile-nav__link"
      aria-current={pathname === item.href ? "page" : undefined}>
      <span className="atlas-mobile-nav__icon"><NavIcon kind={item.key} /></span><span>{language === "ar" ? item.ar : item.label}</span>
    </a>)}
  </nav>;
}
