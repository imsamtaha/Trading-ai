import { NAV_ITEMS } from "@/lib/navigation";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export function Sidebar() {
  return (
    <aside className="atlas-sidebar" data-testid="desktop-sidebar">
      <AtlasWordmark />
      <nav aria-label="Primary navigation" className="atlas-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.key}
            href={item.href}
            className="atlas-nav-link"
            aria-current={item.key === "dashboard" ? "page" : undefined}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
