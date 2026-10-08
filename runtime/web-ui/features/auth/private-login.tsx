"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import Script from "next/script";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createBackendSession, safeReturnTo } from "./session";

type AuthConfig = {
  url: string;
  anon_key: string;
  google_client_id: string;
};

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleIdApi = {
  initialize(options: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: {
    theme?: "outline" | "filled_blue" | "filled_black";
    size?: "small" | "medium" | "large";
    text?: "signin_with" | "signup_with" | "continue_with" | "signin";
    shape?: "rectangular" | "pill" | "circle" | "square";
    width?: number;
    logo_alignment?: "left" | "center";
  }): void;
  cancel?(): void;
  disableAutoSelect?(): void;
};

type GoogleWindow = Window & {
  google?: {
    accounts: {
      id: GoogleIdApi;
    };
  };
};

export function PrivateLogin() {
  const currentReturnTo = () => safeReturnTo(new URLSearchParams(window.location.search).get("returnTo"));
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [clientReady, setClientReady] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [status, setStatus] = useState("Checking secure sign-in…");
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const clientRef = useRef<SupabaseClient | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/backend/auth/config", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Authentication unavailable.");
        return response.json() as Promise<AuthConfig>;
      })
      .then((value) => {
        if (!active) return;
        setConfig(value);
        setStatus("Sign in with Google or use an email link.");
      })
      .catch(() => {
        if (active) setStatus("Authentication is temporarily unavailable.");
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!config?.url || !config.anon_key) return;

    let active = true;
    const client = createClient(config.url, config.anon_key, {
      auth: {
        detectSessionInUrl: true,
        persistSession: true,
        autoRefreshToken: true,
      },
    });

    clientRef.current = client;
    setClientReady(true);

    const query = new URLSearchParams(window.location.search);
    const callback = query.has("code") || query.get("auth") === "callback";
    const callbackError = query.get("error_description");

    if (callbackError) {
      setStatus("Google sign-in could not be completed. Try the Google button again.");
    }

    void client.auth.getSession()
      .then(async ({ data }) => {
        if (!active) return;

        const token = data.session?.access_token;

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
          setStatus("Signed in. Continue to your dashboard.");
        }
      })
      .catch(() => {
        if (active) setStatus("Unable to restore the previous sign-in.");
      });

    return () => {
      active = false;
    };
  }, [config]);

  useEffect(() => {
    if (!googleReady || !clientReady || !config?.google_client_id || !clientRef.current) return;

    const browser = window as GoogleWindow;
    const google = browser.google?.accounts.id;
    const host = document.getElementById("googleLogin");
    const client = clientRef.current;

    if (!google || !host) {
      setStatus("Google sign-in is temporarily unavailable.");
      return;
    }

    host.replaceChildren();

    google.initialize({
      client_id: config.google_client_id,
      auto_select: false,
      cancel_on_tap_outside: true,
      callback: (response) => {
        void (async () => {
          const credential = response.credential;
          if (!credential || busy) return;

          setBusy(true);
          setStatus("Signing in with Google…");

          try {
            const { data, error } = await client.auth.signInWithIdToken({
              provider: "google",
              token: credential,
            });

            if (error || !data.session?.access_token) {
              throw error ?? new Error("Google sign-in did not return a session.");
            }

            await createBackendSession(data.session.access_token);
            window.location.assign(currentReturnTo());
          } catch {
            setBusy(false);
            setStatus("Google sign-in could not be completed. Please try again.");
          }
        })();
      },
    });

    google.renderButton(host, {
      theme: "filled_black",
      size: "large",
      text: "continue_with",
      shape: "pill",
      width: 320,
      logo_alignment: "left",
    });

    return () => {
      google.cancel?.();
    };
  }, [busy, clientReady, config, googleReady]);

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

      const result = await client.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: callback.href,
        },
      });

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
      (window as GoogleWindow).google?.accounts.id.disableAutoSelect?.();
      await fetch("/backend/logout", {
        method: "POST",
        credentials: "same-origin",
      });
      setSignedIn(false);
      setStatus("Signed out.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="atlas-auth-stack">
    <Script
      src="https://accounts.google.com/gsi/client"
      strategy="afterInteractive"
      onReady={() => setGoogleReady(true)}
    />

    <div id="googleLogin" className="atlas-google-login" aria-label="Continue with Google" />

    {!googleReady && <button className="atlas-primary-button atlas-google-oauth" type="button" disabled>
      <span className="atlas-google-mark" aria-hidden="true">G</span>
      <span>Loading Google sign-in…</span>
    </button>}

    <div className="atlas-auth-divider"><span>or</span></div>

    <form className="atlas-email-login" onSubmit={emailLogin}>
      <label htmlFor="atlas-email">Email</label>
      <div className="atlas-email-row">
        <input
          id="atlas-email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
        />
        <button className="atlas-secondary-button" type="submit" disabled={!clientReady || busy}>
          Email link
        </button>
      </div>
    </form>

    {signedIn && <div className="atlas-signed-in-actions">
      <a className="atlas-primary-button" href={currentReturnTo()}>Continue to dashboard</a>
      <button className="atlas-secondary-button" type="button" onClick={signOut} disabled={busy}>
        Sign out
      </button>
    </div>}

    <p id="account-status" className="atlas-auth-status" role="status" aria-live="polite">{status}</p>
  </div>;
}
