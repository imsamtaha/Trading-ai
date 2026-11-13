# ATLAS Control Center — implementation and release gates

Status: design/audit branch only. Production is unchanged.

## Verified architecture
- Canonical repository: `imsamtaha/Trading-ai`.
- Customer dashboard: `app/dashboard/`; presentation layer: `app/dashboard/trading_hub.py`.
- Shadow evaluation: `app/evolution/engine.py`, with `execution_access=False`.
- Public static build: `scripts/build_website.py` validates an explicit file allowlist.
- Public site and owner entry point: `https://justai-atlas.online/` and `/sam` (links in repository; availability and owner authorization not verified).

## Proposed Control Center navigation
Overview | Market Analysis | Shadow Learning | MT5 Demo | Agent Monitor | Paper Journal | Risk & Audit

Each panel must render only authenticated, server-authorized information. Missing, stale or unverified records show **Unavailable / Unverified** rather than fabricated metrics. Never display an inferred P/L as an actual trading result.

## Implementation constraints
1. Reuse existing identity provider, owner-role checks, session handling and RLS; do not introduce an alternate owner bypass.
2. Expose read-only adapters for market analysis, agent status, settled PAPER journal and MT5 DEMO connectivity. All returned records include source, timestamp, mode and freshness.
3. Make command controls disabled by default until a server-side authorization and PAPER-only guard succeeds. Never add live order routes or import broker execution adapters into training or UI endpoints.
4. Preserve `ATLAS_LIVE_TRADING=false`, `ATLAS_DASHBOARD_ONLY=true`, and `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false` as safe defaults.
5. Add Arabic RTL layout tests at 360px, 393px and 412px viewport widths, keyboard focus and minimum 44px touch targets.
6. Do not edit the production database, auth policies, secrets, DNS, payment settings or deployment config without separately verifying impact.

## Required automated tests before merge
- Anonymous request to `/sam` is redirected or rejected; non-owner access is denied.
- Owner login, logout, session expiry and CSRF protection behave as currently designed.
- Read-only API responses carry mode=PAPER or DEMO, source and timestamp; stale or absent data fails closed.
- UI command buttons cannot bypass server-side owner and PAPER safety gates.
- Market Analysis and Shadow Learning show unavailable states when data is missing.
- MT5 demo disconnected state is explicit; no broker order submission occurs.
- RTL Android viewport checks for overflow, navigation, focus, and touch.
- Existing Python/Node tests and GitHub CI pass; production `/health` and `/sam` are checked only after approved deployment.

## Release decision
BLOCKED until actual implementation, authenticated tests, CI, and deployment access are verified. Do not merge to main or publish based on this checklist alone.
