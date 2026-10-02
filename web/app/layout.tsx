import type { Metadata } from "next";
import "./globals.css";
import { OfflineReady } from "./offline-ready";
import { VisitTracker } from "./visit-tracker";

export const metadata: Metadata = {
  title: "ATLAS THE ULTIMATE",
  description: "ATLAS AI trading intelligence and risk-control workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><OfflineReady /><VisitTracker />{children}</body>
    </html>
  );
}
