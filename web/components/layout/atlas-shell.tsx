import type { ReactElement, ReactNode } from "react";
import { AtlasWordmark } from "../brand/atlas-wordmark";
import { MobileNav } from "./mobile-nav";
import { Sidebar } from "./sidebar";
import type { Destination } from "../../lib/navigation";
import { LiveBackendStatus } from "../system/backend-status";

export function AtlasAppShell({
  children,
  active = "dashboard",
}: {
  children?: ReactNode;
  active?: Destination;
}): ReactElement {
  return (
    <div className="atlas-shell" data-testid="atlas-app-shell">
      <Sidebar active={active} />
      <div className="atlas-shell__workspace">
        <header className="atlas-topbar">
          <div className="atlas-topbar__brand">
            <AtlasWordmark />
          </div>
          <div className="atlas-topbar__status"><LiveBackendStatus /></div>
        </header>
        <main className="atlas-main">{children}</main>
      </div>
      <MobileNav active={active} />
    </div>
  );
}
