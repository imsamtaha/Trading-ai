import type { ReactElement } from "react";
import { AtlasWordmark } from "../brand/atlas-wordmark";
import { NAV_ITEMS, type Destination } from "../../lib/navigation";

export function Sidebar({ active }: { active: Destination }): ReactElement {
  return (
    <aside className="atlas-sidebar" data-testid="desktop-sidebar">
      <AtlasWordmark />
      <nav aria-label="Primary navigation" className="atlas-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <a
            className="atlas-nav-link"
            href={item.href}
            key={item.id}
            aria-current={active === item.id ? "page" : undefined}
          >
            <span className="atlas-nav-link__mark" aria-hidden="true">
              {item.label.slice(0, 1)}
            </span>
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
      <p className="atlas-sidebar__footer">Personal workspace</p>
    </aside>
  );
}
