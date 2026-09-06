# Google sign-up activation

The browser integration uses Supabase Auth's PKCE flow and the existing
Trading-ai project. Only its publishable client key is bundled. No Google
client secret or Supabase service-role key belongs in website source.

## Current activation blocker

Google is disabled in Supabase and no Google OAuth client exists yet.
The sign-in button checks the provider before redirecting and reports that
setup is pending. Do not describe this as working sign-up until the provider
is enabled and a complete Google login has been verified.

## Google Cloud

1. Create/select the ATLAS Google Cloud project after the owner signs in.
2. Configure Google Auth Platform branding and the external audience.
   The owner must supply the support/contact email and accept any required terms.
3. Create an OAuth client of type **Web application**.
4. Authorized JavaScript origin:
   `https://atlas-market.imsamtaha.chatgpt.site`
5. Authorized redirect URI:
   `https://dursjyqvrquapwwtkhoc.supabase.co/auth/v1/callback`
6. Configure only identity scopes: openid, email, profile.
7. While the Google app is in testing, add the intended test users.
   Complete any Google publishing/verification requirements before a public launch.

## Supabase

In project `dursjyqvrquapwwtkhoc`, Authentication > Sign In / Providers > Google:

- Store the Google client ID and client secret in the provider settings.
- Enable Google; keep nonce validation enabled.
- Preserve existing redirect URLs and add these exact callback URLs:
  - `https://atlas-market.imsamtaha.chatgpt.site/?auth=callback&lang=en`
  - `https://atlas-market.imsamtaha.chatgpt.site/?auth=callback&lang=ar`

The site root handles the callback. It does not use Sites' reserved `/callback`
route. When changing domains, register the new origin and both callback URLs.

## Access boundaries

Sites remains owner-private, with its existing outer sign-in gate. Google sign-in
does not grant access through that gate, start a paid subscription, or grant MT5
permissions. Public access and paid-service authorization remain separate.
Display identity is fetched from Supabase's verified user endpoint. Authorization
for private records remains enforced by existing database RLS policies.

## Build and verify

```sh
pnpm install --frozen-lockfile
pnpm run build:auth
node --test tests/test_google_auth.mjs
python -m pytest -q
python scripts/build_website.py
```

The bundled script is committed so static Vercel/Netlify deployments need no
build service. Rebuild it whenever `frontend/` changes. Only the exact Supabase
origin is allowed by the hosting Content Security Policy for network requests.

Verify a successful signup, returning-user signin, cancellation, reload, Arabic
language preservation, and sign-out after provider setup. Automated tests mock
the provider and do not establish that Google Cloud is configured.
