export const AUTH_ORIGIN = 'https://dursjyqvrquapwwtkhoc.supabase.co';
export const PUBLIC_KEY = 'sb_publishable_cjK8vKESY4aIFrVG78mmnQ_uXKsVAl3';
export const AUTH_OPTIONS = {
  flowType: 'pkce',
  detectSessionInUrl: false,
  persistSession: true,
  autoRefreshToken: true,
  storageKey: 'atlas-google-auth',
};

export function callbackUrl(origin, language) {
  const url = new URL('/', origin);
  url.searchParams.set('auth', 'callback');
  url.searchParams.set('lang', language === 'ar' ? 'ar' : 'en');
  return url.href;
}

export function cleanCallbackUrl(href) {
  const url = new URL(href);
  for (const key of ['code', 'state', 'auth', 'error', 'error_code', 'error_description']) url.searchParams.delete(key);
  // Never retain implicit-flow tokens; this app accepts PKCE codes only.
  if (/access_token|refresh_token|error/.test(url.hash)) url.hash = '';
  return url.pathname + url.search + '#account';
}

export async function googleProviderReady(fetcher) {
  const response = await fetcher(AUTH_ORIGIN + '/auth/v1/settings', {
    headers: {apikey: PUBLIC_KEY},
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error('unavailable');
  const settings = await response.json();
  return !!settings.external?.google && !settings.disable_signup;
}

export async function startGoogleSignIn({auth, fetcher, origin, language}) {
  if (!await googleProviderReady(fetcher)) throw new Error('setup');
  const {data, error} = await auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: callbackUrl(origin, language),
      skipBrowserRedirect: true,
      scopes: 'openid email profile',
    },
  });
  if (error || !data?.url) throw new Error('unavailable');
  const destination = new URL(data.url);
  if (destination.origin !== AUTH_ORIGIN || destination.pathname !== '/auth/v1/authorize') throw new Error('unavailable');
  return destination.href;
}

export async function finishGoogleSignIn({auth, href, replaceUrl}) {
  const url = new URL(href);
  const callback = url.searchParams.get('auth') === 'callback';
  if (callback || url.searchParams.has('code') || url.searchParams.has('error') || /access_token|refresh_token|error/.test(url.hash)) {
    // Clear sensitive URL data before any network call or error presentation.
    replaceUrl(cleanCallbackUrl(href));
    if (!callback || url.searchParams.has('error') || !url.searchParams.get('code')) throw new Error('callback');
    const {error} = await auth.exchangeCodeForSession(url.searchParams.get('code'));
    if (error) throw new Error('callback');
  }
  const {data, error} = await auth.getUser();
  if (error) {
    if (error.name === 'AuthSessionMissingError') return null;
    throw new Error('session');
  }
  return data.user;
}
