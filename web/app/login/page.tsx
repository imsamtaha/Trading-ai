import Script from "next/script";
export default function LoginPage() {
  return <main className="atlas-login">
    <div className="atlas-login-art" aria-hidden="true"><div className="atlas-login-orbit">A</div><span>ATLAS INTELLIGENCE</span></div>
    <section className="atlas-card atlas-login-card" aria-labelledby="login-title">
      <span className="eyebrow">ATLAS / ACCESS</span><h1 id="login-title">Welcome to ATLAS.</h1>
      <p>Sign in to your account with Google. Trading access is configured separately.</p>
      <button className="atlas-primary-button" type="button" id="google-sign-in">Continue with Google</button>
      <button className="atlas-secondary-button" type="button" id="google-sign-out" hidden>Sign out</button>
      <p id="account-status" role="status" aria-live="polite">Checking sign-in availability…</p>
      <p className="atlas-login-note">Signing in does not connect a broker or activate a subscription.</p>
      <a href="/dashboard">View dashboard ↗</a>
    </section>
    <Script src="/legacy-auth.js" strategy="afterInteractive" />
  </main>;
}
