"""Account identity controls shared with the existing Supabase auth bundle."""

ACCOUNT_PANEL = r'''
<section id="account" class="card atlas-account" aria-labelledby="atlas-account-title">
  <div>
    <div class="label" data-hub-en="YOUR ATLAS ACCOUNT" data-hub-ar="حسابك على ATLAS">YOUR ATLAS ACCOUNT</div>
    <h2 id="atlas-account-title" data-hub-en="Sign in with Google" data-hub-ar="تسجيل الدخول باستخدام Google">Sign in with Google</h2>
    <p class="mini" data-hub-en="Use your Google account to create or access your ATLAS profile." data-hub-ar="استخدم حساب Google لإنشاء ملفك على ATLAS أو الدخول إليه.">Use your Google account to create or access your ATLAS profile.</p>
  </div>
  <div class="atlas-account-controls">
    <button class="btn primary" type="button" id="google-sign-in">Continue with Google</button>
    <button class="btn" type="button" id="google-sign-out" hidden>Sign out</button>
    <p id="account-status" role="status" aria-live="polite">Checking sign-in availability…</p>
    <p class="mini" data-hub-en="Signing in does not connect a broker or activate a subscription. Trading access is configured separately." data-hub-ar="تسجيل الدخول لا يربط حساب الوسيط ولا يفعّل اشتراكاً. صلاحية التداول تُعدّ بشكل منفصل.">Signing in does not connect a broker or activate a subscription. Trading access is configured separately.</p>
    <details>
      <summary data-hub-en="Account privacy" data-hub-ar="خصوصية الحساب">Account privacy</summary>
      <p class="mini" data-hub-en="Google shares your name and email with ATLAS through Supabase Auth. This browser stores your session. Signing out clears this browser session; it does not delete your account." data-hub-ar="يشارك Google اسمك وبريدك الإلكتروني مع ATLAS عبر Supabase Auth. تُحفظ الجلسة في هذا المتصفح. تسجيل الخروج ينهي هذه الجلسة ولا يحذف حسابك.">Google shares your name and email with ATLAS through Supabase Auth. This browser stores your session. Signing out clears this browser session; it does not delete your account.</p>
    </details>
  </div>
</section>
'''
