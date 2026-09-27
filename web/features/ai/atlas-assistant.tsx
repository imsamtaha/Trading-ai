"use client";

import { useState } from "react";
import type { AgentChatResponse } from "@/lib/api/types";
import { AtlasRobotMark } from "./atlas-robot-mark";

export function AtlasAssistant({ sendMessage }: { sendMessage: (input: { message: string }) => Promise<AgentChatResponse> }) {
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");
  async function submit() {
    if (!prompt.trim() || state === "sending") return;
    setState("sending"); setAnswer("");
    try { const result = await sendMessage({ message: prompt }); setAnswer(result.message); setState("success"); }
    catch { setState("error"); }
  }
  return (
    <section className="atlas-card atlas-assistant" id="ai">
      <div className="atlas-assistant-head"><AtlasRobotMark /><div><span className="atlas-card-label">ATLAS AI</span><h2>Right Hand</h2></div></div>
      <p className="atlas-assistant-copy">Ask about market context, signals, account risk, or recent activity.</p>
      {answer && <div className="atlas-assistant-answer">{answer}</div>}
      {state === "error" && <div className="atlas-warning">Assistant unavailable</div>}
      <label className="atlas-assistant-input"><span>Ask ATLAS</span><input aria-label="Ask ATLAS" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Explain this setup…" /></label>
      <button className="atlas-primary-button" type="button" onClick={submit} disabled={state === "sending"}>{state === "sending" ? "Sending…" : "Send"}</button>
    </section>
  );
}
