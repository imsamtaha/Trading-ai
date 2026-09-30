"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Script from "next/script";
import { createBackendSession, startGoogleOAuth } from "./session";

type AuthClient = {
  auth: {
    signInWithIdToken(input: { provider: "google"; token: string }): Promise<{ data: { session?: { access_token?: string } | null }; error?: { message: string } | null }>;
    signInWithOAuth(input: { provider: "google"; options: { redirectTo: string } }): Promise<{ data: { url?: string | null }; error?: { message: string } | null }>;
    signInWithOtp(input: { email: string; options: { emailRedirectTo: string } }): Promise<{ error?: { message: string } | null }>;
    getSession(): Promise<{ data: { session?: { access_token?: string } | null } }>;
    signOut(): Promise<unknown>;
  };
};
type AuthConfig = { url: string; anon_key: string; google_client_id: string };
type AuthWindow = Window & {
  supabase?: { createClient(url: string, key: string): AuthClient };
  google?: { accounts: { id: {
    initialize(input: { client_id: string; callback(response: { credential?: string }): void; use_fedcm_for_prompt: boolean }): void;
    renderButton(element: HTMLElement, input: { theme: string; size: string; text: string }): void;
  } } };
};
export function PrivateLogin() {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [supabaseReady, setSupabaseReady] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [oauthFallback, setOauthFallback] = useState(false);
  const [status, setStatus] = useState("Checking sign-in availability…");
  const [signedIn, setSignedIn] = useState(false);
  const clientRef = useRef<AuthClient | null>(null);
  useEffect(() => {
    let active = true;
    fetch("/backend/auth/config", { cache: "no-store" })
      .then((response) => { if (!response.ok) throw new Error("Authentication unavailable."); return response.json() as Promise<AuthConfig>; })
      .then((value) => { if (active) setConfig(value); })
      .catch(() => { if (active) setStatus("Authentication unavailable."); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!config || !supabaseReady) return;
    const browser = window as AuthWindow;
    if (!config.url || !config.anon_key || !browser.supabase) {
      setStatus("Authentication is not configured."); return;
    }
    let active = true;
    const client = browser.supabase.createClient(config.url, config.anon_key);
    clientRef.current = client;
    const container = document.getElementById("googleLogin");
    if (!container) return;
    container.replaceChildren();
    if (config.google_client_id && browser.google && googleReady) browser.google.accounts.id.initialize({
      client_id: config.google_client_id, use_fedcm_for_prompt: true,
      callback: async ({ credential }) => {
        if (!active || !credential) return;
        setStatus("Signing in…");
        try {
          const result = await client.auth.signInWithIdToken({ provider: "google", token: credential });
          if (result.error) throw new Error(result.error.message);
          const token = result.data.session?.access_token;
          if (!token) throw new Error("Google sign-in did not create a session.");
          await createBackendSession(token);
          window.location.assign("/dashboard");
        } catch { if (active) setStatus("Sign-in failed. Please try again."); }
      },
    });
    if (config.google_client_id && browser.google && googleReady) {
      browser.google.accounts.id.renderButton(container, { theme: "outline", size: "large", text: "continue_with" });
      setStatus("Sign in with Google or request an email code.");
    } else if (!config.google_client_id) {
      setOauthFallback(true);
      setStatus("Sign in with Google or request an email code.");
    }
    void client.auth.getSession().then(async ({ data }) => {
      if (!active) return;
      const token = data.session?.access_token;
      if (token && (new URLSearchParams(window.location.search).has("code") || new URLSearchParams(window.location.search).get("auth") === "callback")) {
        try { await createBackendSession(token); window.location.assign("/dashboard"); }
        catch { if (active) setStatus("Sign-in failed. Please try again."); }
      } else setSignedIn(Boolean(token));
    }).catch(() => { if (active) setStatus("Unable to restore sign-in."); });
    return () => { active = false; };
  }, [config, supabaseReady, googleReady]);
  async function googleOAuth() {
    if (!clientRef.current || !config) return;
    setStatus("Redirecting to Google…");
    try {
      const url = await startGoogleOAuth(clientRef.current.auth, window.location.origin, config.url);
      window.location.assign(url);
    } catch { setStatus("Google sign-in unavailable. Please try again."); }
  }
  async function emailLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const client = clientRef.current;
    if (!client) return;
    const email = String(new FormData(event.currentTarget).get("email") || "");
    const result = await client.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin + "/?auth=callback" } });
    setStatus(result.error?.message ?? "Check your email for the sign-in link.");
  }
  async function signOut() {
    await clientRef.current?.auth.signOut();
    await fetch("/backend/logout", { method: "POST", credentials: "same-origin" });
    setSignedIn(false);
    setStatus("Signed out.");
  }
  return <>
    <Script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" onReady={() => setSupabaseReady(true)} />
    <Script src="https://accounts.google.com/gsi/client" onReady={() => setGoogleReady(true)} />
    {oauthFallback ? <button className="atlas-primary-button" type="button" onClick={googleOAuth}>Continue with Google</button> : <span>Continue with Google</span>}<div id="googleLogin" className="atlas-google-login" />
    <form className="atlas-email-login" onSubmit={emailLogin}><label htmlFor="atlas-email">Email</label><input id="atlas-email" name="email" type="email" autoComplete="email" required /><button className="atlas-primary-button" type="submit">Email code</button></form>
    {signedIn && <button className="atlas-secondary-button" type="button" onClick={signOut}>Sign out</button>}
    <p id="account-status" role="status" aria-live="polite">{status}</p>
  </>;
}
