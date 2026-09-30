import { atlasFetch, AtlasApiError } from "./client";
import { apiPath } from "./config";
import type { AgentChatRequest, AgentChatResponse } from "./types";
export async function sendAgentMessage(input: AgentChatRequest): Promise<AgentChatResponse> {
  const endpoint = apiPath("/api/user/assistant");
  const raw = await atlasFetch<Record<string, unknown>>(endpoint, {
    method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: input.message }),
  }, 20000);
  const message = raw.message ?? raw.response ?? raw.answer;
  if (typeof message !== "string" || !message.trim()) throw new AtlasApiError(endpoint, 200, "ATLAS assistant returned no answer");
  return { message };
}
