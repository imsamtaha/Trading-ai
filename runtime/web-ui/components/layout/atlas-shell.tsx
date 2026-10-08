import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { MobileNav } from "./mobile-nav";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export function AtlasShell({ children }: { children: ReactNode }) {
  return (
    <div className="atlas-layout">
      <Sidebar />
      <main className="atlas-main"><div className="atlas-mobile-brand"><AtlasWordmark /></div>{children}</main>
      <MobileNav />
    </div>
  );
}
