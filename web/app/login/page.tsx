import { PrivateLogin } from "@/features/auth/private-login";
export default function LoginPage() {
  return <main className="atlas-login">
    <div className="atlas-login-art" aria-hidden="true"><div className="atlas-login-orbit">A</div><span>ATLAS INTELLIGENCE</span></div>
    <section className="atlas-card atlas-login-card" aria-labelledby="login-title">
      <span className="eyebrow">ATLAS / ACCESS</span><h1 id="login-title">Welcome to ATLAS.</h1>
      <p>Sign in to your private account. Trading access is configured separately.</p>
      <PrivateLogin />
      <p className="atlas-login-note">Signing in does not connect a broker or activate a subscription.</p>
      <a href="/dashboard">View dashboard ↗</a>
    </section>
  </main>;
}
