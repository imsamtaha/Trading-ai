import { atlasFetch } from "./client";
import type { AgentChatRequest, AgentChatResponse } from "./types";

export async function sendAgentMessage(input: AgentChatRequest): Promise<AgentChatResponse> {
  const raw = await atlasFetch<Record<string, unknown>>("/agent/right-hand/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
  const message = raw.message ?? raw.response ?? raw.answer ?? "";
  return { message: typeof message === "string" ? message : String(message) };
}
