"use client";

import { useEffect } from "react";

export function VisitTracker() {
  useEffect(() => {
    void fetch("/backend/api/runtime/visit", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ page: window.location.pathname }),
      keepalive: true,
    }).catch(() => {});
  }, []);
  return null;
}
