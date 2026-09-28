export class AtlasApiError extends Error {
  readonly endpoint: string;
  readonly status: number | null;
  constructor(message: string, endpoint: string, status: number | null = null) {
    super(message); this.name = "AtlasApiError"; this.endpoint = endpoint; this.status = status;
  }
}

import { ATLAS_API_BASE_URL } from "./config";
const API_BASE = ATLAS_API_BASE_URL;

export async function requestJson<T>(endpoint: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = 10000, ...requestOptions } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, { ...requestOptions, signal: controller.signal, headers: { Accept: "application/json", ...requestOptions.headers } });
    if (!response.ok) throw new AtlasApiError(`ATLAS API returned HTTP ${response.status}`, endpoint, response.status);
    try { return await response.json() as T; }
    catch { throw new AtlasApiError("ATLAS API returned invalid JSON", endpoint, response.status); }
  } catch (error) {
    if (error instanceof AtlasApiError) throw error;
    const message = error instanceof DOMException && error.name === "AbortError" ? "ATLAS API request timed out" : "ATLAS API request failed";
    throw new AtlasApiError(message, endpoint);
  } finally { clearTimeout(timer); }
}
