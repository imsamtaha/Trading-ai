"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Script from "next/script";
import { createBackendSession, safeReturnTo, startGoogleOAuth } from "./session";

type AuthClient = {
  auth: {
    signInWithOAuth(input: { provider: "google"; options: { redirectTo: string; skipBrowserRedirect: true } }): Promise<{ data: { url?: string | null }; error?: { message: string } | null }>;
    signInWithOtp(input: { email: string; options: { emailRedirectTo: string } }): Promise<{ error?: { message: string } | null }>;
    getSession(): Promise<{ data: { session?: { access_token?: string } | null } }>;
    signOut(): Promise<unknown>;
  };
};
type AuthConfig = { url: string; anon_key: string; google_client_id: string };
type AuthWindow = Window & { supabase?: { createClient(url: string, key: string): AuthClient } };

export function PrivateLogin() {
  const currentReturnTo = () => safeReturnTo(new URLSearchParams(window.location.search).get("returnTo"));
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [supabaseReady, setSupabaseReady] = useState(false);
  const [clientReady, setClientReady] = useState(false);
  const [status, setStatus] = useState("Checking secure sign-in…");
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const clientRef = useRef<AuthClient | null>(null);
  const failedReturn = useRef(false);

  useEffect(() => {
    let active = true;
    const returnedUrl = new URL(window.location.href);
    const fragment = new URLSearchParams(returnedUrl.hash.slice(1));
    failedReturn.current = failedReturn.current || returnedUrl.searchParams.has("error") || fragment.has("error");
    if (failedReturn.current) {
      for (const key of ["error", "error_code", "error_description", "code"]) returnedUrl.searchParams.delete(key);
      window.history.replaceState({}, "", returnedUrl.pathname + returnedUrl.search);
    }
    fetch("/backend/auth/config", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Authentication unavailable.");
        return response.json() as Promise<AuthConfig>;
      })
      .then((value) => {
        if (active) {
          setConfig(value);
          setStatus(failedReturn.current ? "Google sign-in could not be completed. Use the email link or contact ATLAS support." : "Sign in with Google or use an email link.");
        }
      })
      .catch(() => { if (active) setStatus("Authentication is temporarily unavailable."); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!config || !supabaseReady) return;
    const browser = window as AuthWindow;
    if (!config.url || !config.anon_key || !browser.supabase) {
      setStatus("Authentication is not configured.");
      return;
    }

    let active = true;
    const client = browser.supabase.createClient(config.url, config.anon_key);
    clientRef.current = client;
    setClientReady(true);
    setStatus(failedReturn.current ? "Google sign-in could not be completed. Use the email link or contact ATLAS support." : "Sign in with Google or use an email link.");

    void client.auth.getSession().then(async ({ data }) => {
      if (!active || failedReturn.current) return;
      const token = data.session?.access_token;
      const query = new URLSearchParams(window.location.search);
      const callback = query.has("code") || query.get("auth") === "callback";

      if (token && callback) {
        setBusy(true);
        setStatus("Finishing sign-in…");
        try {
          await createBackendSession(token);
          window.location.assign(currentReturnTo());
        } catch {
          if (active) {
            setBusy(false);
            setStatus("Sign-in could not be completed. Please try again.");
          }
        }
      } else if (token) {
        setSignedIn(true);
        setStatus("Signed in. Continue to your account.");
      }
    }).catch(() => {
      if (active) setStatus("Unable to restore the previous sign-in.");
    });

    return () => { active = false; };
  }, [config, supabaseReady]);

  async function googleOAuth() {
    if (!clientRef.current || !config || busy) {
      if (!busy) setStatus("Secure sign-in is still loading. Try again in a moment.");
      return;
    }
    setBusy(true);
    setStatus("Opening Google sign-in…");
    try {
      const url = await startGoogleOAuth(clientRef.current.auth, window.location.origin, config.url, currentReturnTo());
      window.location.assign(url);
    } catch {
      setBusy(false);
      setStatus("Google sign-in is unavailable right now. You can use the email link instead.");
    }
  }

  async function emailLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const client = clientRef.current;
    if (!client || busy) {
      if (!busy) setStatus("Secure sign-in is still loading. Try again in a moment.");
      return;
    }

    const email = String(new FormData(event.currentTarget).get("email") || "").trim();
    if (!email) return;

    setBusy(true);
    setStatus("Sending your secure sign-in link…");
    try {
      const callback = new URL("/login", window.location.origin);
      callback.searchParams.set("auth", "callback");
      callback.searchParams.set("returnTo", currentReturnTo());
      const result = await client.auth.signInWithOtp({ email, options: { emailRedirectTo: callback.href } });
      setStatus(result.error?.message ?? "Check your email for the secure sign-in link.");
    } catch {
      setStatus("Email sign-in is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    try {
      await clientRef.current?.auth.signOut();
      await fetch("/backend/logout", { method: "POST", credentials: "same-origin" });
      setSignedIn(false);
      setStatus("Signed out.");
    } finally {
      setBusy(false);
    }
  }

  const ready = Boolean(config && supabaseReady && clientReady);

  return <div className="atlas-auth-stack">
    <Script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" onReady={() => setSupabaseReady(true)} />

    <button className="atlas-primary-button atlas-google-oauth" type="button" onClick={googleOAuth} disabled={!ready || busy}>
      <span className="atlas-google-mark" aria-hidden="true">G</span>
      <span>{busy ? "Please wait…" : "Continue with Google"}</span>
    </button>

    <div id="googleLogin" className="atlas-google-login" aria-hidden="true" />

    <div className="atlas-auth-divider"><span>or</span></div>

    <form className="atlas-email-login" onSubmit={emailLogin}>
      <label htmlFor="atlas-email">Email</label>
      <div className="atlas-email-row">
        <input id="atlas-email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
        <button className="atlas-secondary-button" type="submit" disabled={!ready || busy}>Email link</button>
      </div>
    </form>

    {signedIn && <div className="atlas-signed-in-actions">
      <a className="atlas-primary-button" href={currentReturnTo()}>Continue to account</a>
      <button className="atlas-secondary-button" type="button" onClick={signOut} disabled={busy}>Sign out</button>
    </div>}

    <p id="account-status" className="atlas-auth-status" role="status" aria-live="polite">{status}</p>
  </div>;
}
