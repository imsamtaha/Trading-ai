import type { ReactElement } from "react";
import { NAV_ITEMS, type Destination } from "../../lib/navigation";

export function MobileNav({ active }: { active: Destination }): ReactElement {
  return (
    <nav aria-label="Mobile navigation" className="atlas-mobile-nav" data-testid="mobile-nav">
      {NAV_ITEMS.map((item) => (
        <a
          className="atlas-mobile-nav__link"
          href={item.href}
          key={item.id}
          aria-current={active === item.id ? "page" : undefined}
        >
          <span className="atlas-mobile-nav__mark" aria-hidden="true">
            {item.label.slice(0, 1)}
          </span>
          <span>{item.label}</span>
        </a>
      ))}
    </nav>
  );
}
