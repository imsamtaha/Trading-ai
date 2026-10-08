import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { MobileNav } from "./mobile-nav";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export function AtlasShell({ children, language = "ar" }: { children: ReactNode; language?: "ar" | "en" }) {
  return (
    <div className="atlas-layout" lang={language} dir={language === "ar" ? "rtl" : "ltr"}>
      <Sidebar language={language} />
      <main className="atlas-main"><div className="atlas-mobile-brand"><AtlasWordmark /></div>{children}</main>
      <MobileNav language={language} />
    </div>
  );
}
