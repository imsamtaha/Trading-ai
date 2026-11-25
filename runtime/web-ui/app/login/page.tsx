import { PrivateLogin } from "@/features/auth/private-login";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export default function LoginPage() {
  return <main className="atlas-login">
    <section className="atlas-login-art" aria-label="ATLAS workspace">
      <div className="atlas-login-brand-shell"><AtlasWordmark /></div>
      <span className="atlas-login-mode">PAPER INTELLIGENCE WORKSPACE</span>
      <h2>One secure sign-in.<br />Your ATLAS workspace.</h2>
      <p>Market intelligence, Council analysis, Paper monitoring, and training context in one focused dashboard.</p>
      <div className="atlas-login-points" aria-label="ATLAS access features">
        <span>Paper-first workspace</span>
        <span>Private session</span>
        <span>Risk-focused intelligence</span>
      </div>
    </section>

    <section className="atlas-card atlas-login-card" aria-labelledby="login-title">
      <div className="atlas-login-card-head">
        <span className="eyebrow">ATLAS / SECURE ACCESS</span>
        <span className="atlas-login-secure-dot">Encrypted session</span>
      </div>
      <h1 id="login-title">Sign in to ATLAS</h1>
      <p className="atlas-login-lead">Continue to your private dashboard. Signing in does not connect a broker or enable broker execution.</p>

      <PrivateLogin />

      <div className="atlas-login-foot">
        <p className="atlas-login-note">Your dashboard remains Paper-only. Account connection and product access are handled separately.</p>
        <a className="atlas-login-back" href="/dashboard">← Open ATLAS dashboard</a>
      </div>
    </section>
  </main>;
}
