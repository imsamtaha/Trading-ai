"use client";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/navigation";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export function Sidebar({ language = "ar" }: { language?: "ar" | "en" }) {
  const pathname = usePathname();
  return (
    <aside className="atlas-sidebar" data-testid="desktop-sidebar">
      <AtlasWordmark />
      <nav aria-label={language === "ar" ? "التنقل الجانبي" : "Primary navigation"} className="atlas-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.key}
            href={item.href}
            aria-current={pathname === item.href ? "page" : undefined}
            className="atlas-nav-link"
          >
            {language === "ar" ? item.ar : item.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
