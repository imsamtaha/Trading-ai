export class AtlasApiError extends Error {
  constructor(public endpoint: string, public status: number | null, message: string) {
    super(message);
    this.name = "AtlasApiError";
  }
}

export async function atlasFetch<T = unknown>(endpoint: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint, init);
  } catch (error) {
    throw new AtlasApiError(endpoint, null, error instanceof Error ? error.message : "Network request failed");
  }
  if (!response.ok) throw new AtlasApiError(endpoint, response.status, `ATLAS API request failed (${response.status})`);
  try {
    return await response.json() as T;
  } catch {
    throw new AtlasApiError(endpoint, response.status, "ATLAS API returned invalid JSON");
  }
}
