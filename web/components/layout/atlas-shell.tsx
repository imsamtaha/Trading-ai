import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { MobileNav } from "./mobile-nav";

export function AtlasShell({ children }: { children: ReactNode }) {
  return (
    <div className="atlas-layout">
      <Sidebar />
      <main className="atlas-main">{children}</main>
      <MobileNav />
    </div>
  );
}
