import { requestJson } from "./client";
import type { AgentChatRequest, AgentChatResponse } from "./types";
export function sendAgentMessage(input: AgentChatRequest): Promise<AgentChatResponse> {
  return requestJson<AgentChatResponse>("/agent/right-hand/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
}
