import { NAV_ITEMS } from "@/lib/navigation";

export function MobileNav() {
  return (
    <nav className="atlas-mobile-nav" data-testid="mobile-nav" aria-label="Mobile navigation">
      {NAV_ITEMS.map((item) => (
        <a
          key={item.key}
          href={item.href}
          className="atlas-mobile-nav__link"
          aria-current={item.key === "dashboard" ? "page" : undefined}
        >
          {item.label}
        </a>
      ))}
    </nav>
  );
}
