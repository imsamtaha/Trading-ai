export async function startGoogleOAuth(
  auth: { signInWithOAuth(input: { provider: "google"; options: { redirectTo: string } }): Promise<{ data: { url?: string | null }; error?: { message: string } | null }> },
  origin: string, supabaseUrl: string,
): Promise<string> {
  const result = await auth.signInWithOAuth({ provider: "google", options: { redirectTo: `${origin}/?auth=callback` } });
  if (result.error || !result.data.url) throw new Error("Google OAuth unavailable.");
  const target = new URL(result.data.url);
  if (target.protocol !== "https:" || target.origin !== new URL(supabaseUrl).origin || target.pathname !== "/auth/v1/authorize") {
    throw new Error("Invalid Google OAuth redirect.");
  }
  return target.href;
}

export async function createBackendSession(token: string, fetcher: typeof fetch = fetch): Promise<void> {
  const response = await fetcher("/backend/auth/session", {
    method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" },
    body: JSON.stringify({ access_token: token }),
  });
  if (!response.ok) throw new Error("Unable to create a private ATLAS session.");
}
