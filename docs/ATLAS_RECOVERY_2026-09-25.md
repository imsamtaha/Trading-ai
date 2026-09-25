# ATLAS recovery status — 25 September 2026

## Verified

- `main` snapshot inspected: `cb03f28044991156cae9a986d5806e18fbc9a022`.
- Supabase project `dursjyqvrquapwwtkhoc` is `ACTIVE_HEALTHY`.
- Google provider and signup are enabled in the public Auth settings.
- All nine public tables have RLS enabled. No broker connection or execution
  records were present during inspection; this does not establish the state
  of a separate Windows terminal.
- Applied `20260925002424_restrict_rls_auto_enable_execution`: the internal
  `rls_auto_enable()` event-trigger helper is no longer executable by `PUBLIC`,
  `anon`, or `authenticated`. Owner/service-role execution remains available,
  `ensure_rls` remains enabled, and the security advisor returns no lints.
- Local validation after UI repairs: 301 pytest tests and six subtests passed;
  10 JavaScript tests passed; the public website builder passed.
- Local API smoke check: `/` 200, `/dashboard` 308 to `/`, `/health` 200,
  `/assets/google-auth.js` 200, and the dashboard-only execution guard returns
  403 for `/mt5/test-order`.

## Repairs included

- Attach section IDs to the actual account and market headings, fixing the
  Trading Hub navigation links.
- Add the existing Google Auth controls to the canonical page, where the
  configured OAuth callback returns. Move the broker display to `brokerAccount`
  to avoid colliding with the OAuth `#account` target.
- Handle both existing language event surfaces; rebuild the pinned auth bundle.
- Make account controls stack on phones, preserve hidden control state, improve
  light-theme contrast, wrap long account text, and honor reduced motion.
- Replace the unconditional green MT5 header badge with a neutral workspace
  label. Account connection status must come from telemetry.

Google identity UI is not backend authorization or a verified broker connection.
Existing access controls remain necessary. No successful user OAuth session or
real broker execution was claimed by these tests.

## Cloudflare blocker and recovery

The production hostname `https://justai-atlas.online` returned HTTP 403 with
Cloudflare **Error 1000: DNS points to prohibited IP**. This is a DNS/proxy
routing failure; the origin application was not reached by this request.

1. Connect the Windows host in Remote Desktop Commander and Opera Browser
   Connector (`Allow AI connection`). Neither connection was available during
   this repair session.
2. In Cloudflare, inspect the named tunnel and its connector health. Confirm
   the route for `justai-atlas.online` targets the actual ATLAS listener on the
   Windows host (the repository public launcher defaults to port 8000).
3. Inspect the current apex DNS A/AAAA/CNAME records before changing them.
   For a named tunnel, use the CNAME target supplied by that tunnel's dashboard;
   do not copy a Cloudflare edge IP from DNS lookup results into an A record.
   Remove or replace only the conflicting web route. Keep mail records intact.
4. Deploy the reviewed GitHub commit to the Windows checkout without overwriting
   local changes or printing `.env`, broker passwords, or tunnel tokens.
5. Start/restart the application and named tunnel, then verify `/`, `/health`,
   the legacy dashboard redirect, sign-in callback, and mobile Arabic/English
   rendering externally. Verify existing access policies for private telemetry.

Do not report deployment complete until these checks pass. The launcher
`start_atlas_public.ps1` starts a **Quick Tunnel**; it does not configure the
production domain or replace a named tunnel service.

Reference: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1000/

## Outstanding validation

- Windows MT5 connectivity, terminal account mode, and telemetry freshness.
- Production DNS/tunnel routing and Cloudflare Access policies.
- A complete Google sign-in/sign-out round trip on the production origin.
- Visual mobile and desktop inspection. The browser in this session could not
  access the local preview (`ERR_BLOCKED_BY_CLIENT`).
- Existing separate PRs for execution modes, test orchestration, and Agents API
  were not merged as part of this focused dashboard repair.
