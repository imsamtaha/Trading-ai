"use client";
import { useEffect } from "react";

export function OfflineReady() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/atlas-offline-sw.js").catch(() => {});
    }
  }, []);
  return null;
}
