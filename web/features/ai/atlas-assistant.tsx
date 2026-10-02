"use client";

import Image from "next/image";
import { useState } from "react";
import type { AgentChatResponse } from "@/lib/api/types";
import { AgentBadge } from "@/components/system/agent-badge";

export function AtlasAssistant({ sendMessage, language = "ar" }: { sendMessage: (input: { message: string }) => Promise<AgentChatResponse>; language?: "ar" | "en" }) {
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");
  async function submit() {
    if (!prompt.trim() || state === "sending") return;
    setState("sending"); setAnswer("");
    try { const result = await sendMessage({ message: prompt }); setAnswer(result.message); setState("success"); }
    catch { setState("error"); }
  }
  const ar = language === "ar";
  return (
    <section className="atlas-card atlas-assistant atlas-feature-3d" id="ai">
      <div className="atlas-assistant-head"><Image className="atlas-assistant-logo" src="/atlas-logo.webp" alt="ATLAS AI" width={72} height={72} unoptimized /><div><span className="atlas-card-label">ATLAS AI</span><h2 className="atlas-agent-title" dir={ar ? "rtl" : "ltr"}>{ar ? <><span>المساعد الذكي</span><AgentBadge /></> : <><AgentBadge /><span>AI Assistant</span></>}</h2></div></div>
      <p className="atlas-assistant-copy">اسأل ATLAS AI عن الأسواق والمخاطر. لا يرى حسابك أو الأسعار الحية، ولا تشارك بيانات الدخول.</p>
      {answer && <div className="atlas-assistant-answer">{answer}</div>}
      {state === "error" && <div className="atlas-warning">المساعد غير متاح</div>}
      <label className="atlas-assistant-input"><span>اسأل ATLAS</span><input aria-label="اسأل ATLAS" maxLength={1000} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="اسأل عن السوق أو المخاطر…" /></label>
      <button className="atlas-primary-button" type="button" onClick={submit} disabled={state === "sending"}>{state === "sending" ? "جارٍ الإرسال…" : "إرسال"}</button>
    </section>
  );
}
