"use client";

import Image from "next/image";
import { useState } from "react";
import type { AgentChatResponse } from "@/lib/api/types";
import { AgentBadge } from "@/components/system/agent-badge";

export function AtlasAssistant({
  sendMessage,
  language = "ar",
  enabled = true,
  lockedHref = "/login?returnTo=%2Fdashboard",
}: {
  sendMessage: (input: { message: string }) => Promise<AgentChatResponse>;
  language?: "ar" | "en";
  enabled?: boolean;
  lockedHref?: string;
}) {
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");
  const ar = language === "ar";

  async function submit() {
    if (!enabled || !prompt.trim() || state === "sending") return;
    setState("sending");
    setAnswer("");
    try {
      const result = await sendMessage({ message: prompt });
      setAnswer(result.message);
      setPrompt("");
      setState("success");
    } catch {
      setState("error");
    }
  }

  return (
    <section className={"atlas-card atlas-assistant atlas-feature-3d" + (enabled ? "" : " atlas-assistant--locked")} id="ai">
      <div className="atlas-assistant-head">
        <Image className="atlas-assistant-logo" src="/atlas-logo.webp" alt="ATLAS AI" width={72} height={72} unoptimized />
        <div>
          <h2 className="atlas-agent-title atlas-assistant-title" dir={ar ? "rtl" : "ltr"}>
            {ar
              ? <><span className="atlas-assistant-name" dir="ltr">ATLAS AI</span><span>المساعد الذكي</span><AgentBadge /></>
              : <><AgentBadge /><span>AI Assistant</span><span className="atlas-assistant-name" dir="ltr">ATLAS AI</span></>}
          </h2>
        </div>
      </div>

      <p className="atlas-assistant-copy">
        {ar
          ? "اسأل ATLAS AI عن الأسواق والمخاطر ضمن بيئة التداول الورقي. لا تشارك بيانات الدخول."
          : "Ask ATLAS AI about markets and risk inside the Paper workspace. Never share login credentials."}
      </p>

      {answer && <div className="atlas-assistant-answer">{answer}</div>}
      {state === "error" && <div className="atlas-warning">{ar ? "المساعد غير متاح" : "Assistant unavailable"}</div>}

      <label className="atlas-assistant-input">
        <span>{ar ? "اسأل ATLAS" : "Ask ATLAS"}</span>
        <input
          aria-label={ar ? "اسأل ATLAS" : "Ask ATLAS"}
          maxLength={1000}
          disabled={!enabled || state === "sending"}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={enabled
            ? (ar ? "اسأل عن السوق أو المخاطر…" : "Ask about markets or risk…")
            : (ar ? "سجّل الدخول لتفعيل ATLAS AI" : "Sign in to activate ATLAS AI")}
        />
      </label>

      {enabled
        ? <button className="atlas-primary-button" type="button" onClick={submit} disabled={state === "sending"}>
            {state === "sending" ? (ar ? "جارٍ الإرسال…" : "Sending…") : (ar ? "إرسال" : "Send")}
          </button>
        : <a className="atlas-primary-button atlas-assistant-unlock" href={lockedHref}>
            {lockedHref.startsWith("/subscribe")
              ? (ar ? "تفعيل ATLAS AI" : "Activate ATLAS AI")
              : (ar ? "تسجيل الدخول لتفعيل ATLAS AI" : "Sign in to activate ATLAS AI")}
          </a>}
    </section>
  );
}
