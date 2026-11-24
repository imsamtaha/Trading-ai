export function safeReturnTo(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/dashboard";
  return raw;
}

export async function startGoogleOAuth(
  auth: { signInWithOAuth(input: { provider: "google"; options: { redirectTo: string; skipBrowserRedirect: true } }): Promise<{ data: { url?: string | null }; error?: { message: string } | null }> },
  origin: string, supabaseUrl: string, returnTo = "/dashboard",
): Promise<string> {
  const safe = safeReturnTo(returnTo);
  const redirect = new URL("/login", origin);
  redirect.searchParams.set("auth", "callback");
  redirect.searchParams.set("returnTo", safe);
  const result = await auth.signInWithOAuth({ provider: "google", options: { redirectTo: redirect.href, skipBrowserRedirect: true } });
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
