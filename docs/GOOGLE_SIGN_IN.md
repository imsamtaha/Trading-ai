# Google sign-up activation

The browser integration uses Supabase Auth's PKCE flow and the existing
Trading-ai project. Only its publishable client key is bundled. No Google
client secret or Supabase service-role key belongs in website source.

## Provider configuration

Configure Google OAuth in the authorized Supabase project's Authentication settings. Store the Google client ID and secret in the provider settings. Register the exact origin and callback URL used by the deployed authentication client. Review the existing allowed URLs before changing them. This repository does not publish the live site.

Display identity is fetched from Supabase's verified user endpoint. Existing database RLS policies govern private records. Broker and subscription authorization remain separate from sign-in.

## Build and verify

```sh
pnpm install --frozen-lockfile
pnpm run build:auth
node --test tests/test_google_auth.mjs
python -m pytest -q
```

Rebuild the committed authentication bundle after changing `frontend/`. These tests exercise mocked authentication. Verify sign-up, returning sign-in, cancellation, reload, and sign-out against the deployed authentication client separately.
