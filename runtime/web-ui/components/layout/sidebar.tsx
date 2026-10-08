import { NAV_ITEMS } from "@/lib/navigation";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

const ARABIC_LABELS: Record<string, string> = {
  dashboard: "لوحة التحكم", markets: "الأسواق", trade: "التداول", signals: "الإشارات",
  risk: "المخاطر", analytics: "التحليلات", news: "الأخبار", ai: "ATLAS AI", account: "الحساب",
};

export function Sidebar({ language = "ar" }: { language?: "ar" | "en" }) {
  return (
    <aside className="atlas-sidebar" data-testid="desktop-sidebar">
      <AtlasWordmark />
      <nav aria-label={language === "ar" ? "التنقل الجانبي" : "Primary navigation"} className="atlas-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.key}
            href={item.href}
            className="atlas-nav-link"
            aria-current={item.key === "dashboard" ? "page" : undefined}
          >
            {language === "ar" ? ARABIC_LABELS[item.key] : item.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
