export class AtlasApiError extends Error {
  constructor(public endpoint: string, public status: number | null, message: string) {
    super(message);
    this.name = "AtlasApiError";
  }
}
export async function atlasFetch<T = unknown>(endpoint: string, init?: RequestInit, timeoutMs = 12000): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  init?.signal?.addEventListener("abort", abort, { once: true });
  if (init?.signal?.aborted) abort();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => { controller.abort(); reject(new AtlasApiError(endpoint, null, "ATLAS API request timed out")); }, timeoutMs);
  });
  let response: Response;
  try {
    response = await Promise.race([fetch(endpoint, { ...init, signal: controller.signal }), timeout]);
  } catch (error) {
    throw error instanceof AtlasApiError ? error : new AtlasApiError(endpoint, null, error instanceof Error ? error.message : "Network request failed");
  } finally {
    clearTimeout(timer);
    init?.signal?.removeEventListener("abort", abort);
  }
  if (!response.ok) throw new AtlasApiError(endpoint, response.status, `ATLAS API request failed (${response.status})`);
  try { return await response.json() as T; }
  catch { throw new AtlasApiError(endpoint, response.status, "ATLAS API returned invalid JSON"); }
}
