import { PrivateLogin } from "@/features/auth/private-login";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";

export default function LoginPage() {
  return <main className="atlas-login">
    <section className="atlas-login-art" aria-label="ATLAS workspace">
      <div className="atlas-login-brand-shell"><AtlasWordmark /></div>
      <span className="atlas-login-mode">PAPER INTELLIGENCE WORKSPACE</span>
      <h2>One secure sign-in.<br />Your ATLAS workspace.</h2>
      <p>Secure access to ATLAS APIs.</p>
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
      <p className="atlas-login-lead">Sign in to ATLAS services. Signing in does not connect a broker or enable broker execution.</p>

      <PrivateLogin />

      <div className="atlas-login-foot">
        <p className="atlas-login-note">Sign-in grants access to services according to your account permissions.</p>
      </div>
    </section>
  </main>;
}
