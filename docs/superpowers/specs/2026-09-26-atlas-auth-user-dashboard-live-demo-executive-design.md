# ATLAS Auth, User Dashboard, and Live Demo Executive Design

Date: 2026-09-26
Status: Draft for user review

## Goal

Turn ATLAS into a private-by-default multi-user experience. No authenticated user may ever see another user's MT5 account, positions, pending orders, trade history, balance, equity, settings, or demo-executive state.

Users should be able to enter ATLAS with Google or email OTP, reach a private dashboard, keep their data isolated from every other user, and optionally attach an MT5 Demo workspace for read-only market/account telemetry.

The Live Demo Executive will analyze live demo-market data and simulate execution inside ATLAS only. It must never submit a broker order or enable real-money execution.

## Product Flow

1. `/` is a landing page with a prominent `Enter ATLAS` action; it does not expose any MT5 account telemetry.
2. `/login` offers `Continue with Google` and `Email code`.
3. Successful authentication redirects to `/app/dashboard`.
4. `/dashboard` redirects to the authenticated private dashboard or `/login`; there is no shared MT5 dashboard preview.
5. `/app/dashboard` is private and user-scoped.
6. A signed-in user can connect or request an MT5 Demo workspace.
7. The private dashboard shows market telemetry, AI context, demo positions, plan access, and Live Demo Executive state.
8. Logout destroys the local session and returns to `/`.
## Architecture

### Authentication

Use Supabase Auth as the identity provider.

Supported methods:
- Google OAuth.
- Email OTP / magic-link style login.

FastAPI validates the authenticated user before serving private ATLAS APIs. Supabase service credentials remain server-side only. The browser must never receive service-role keys.

### Route Separation

Public routes:
- `/`
- `/login`
- `/dashboard`
- `/health`
- public subscription and payment-information routes

Protected routes:
- `/app/dashboard`
- `/api/me`
- `/api/user/dashboard`
- `/api/user/settings`
- `/api/mt5-demo/*`
- `/api/demo-executive/*`

The existing dashboard-only safety guard must be updated explicitly rather than bypassed.
## User Data and Isolation

Recommended persistent records:
- `profiles`: user id, display name, locale, created/updated timestamps.
- `user_settings`: preferred language, theme, default symbols, notification preferences.
- `subscriptions`: user id, plan, access state, billing reference.
- `mt5_demo_connections`: user id, masked account metadata, server, connection state, timestamps.
- `demo_positions`: user id, symbol, side, entry, simulated P/L, lifecycle timestamps.
- `demo_executive_events`: user id, symbol, context snapshot, simulated decision, reason, timestamp.

Every record is keyed by authenticated user id. Database row-level security must prevent cross-user reads and writes.

MT5 passwords must never be returned to the browser or logged. Do not persist raw broker passwords in application tables. Any temporary credential handling must be server-side and restricted to DEMO accounts.

## MT5 Demo Boundary

ATLAS must verify the connected account is DEMO before exposing user telemetry.

If account type is REAL, UNKNOWN, or cannot be verified, the connector must refuse the session.

The user-facing connector is read-only for broker telemetry. The application keeps `ATLAS_LIVE_TRADING=false` and must not invoke broker order submission from private dashboard or executive routes.
## Live Demo Executive

The Live Demo Executive is a simulation engine, not a broker executor.

Pipeline:
1. Read the latest MT5 Demo telemetry and market snapshot.
2. Normalize the symbol and classify the asset.
3. Build ATLAS context: trend, momentum, volatility, risk, spread quality, confidence, and data freshness.
4. Apply deterministic risk rules before any simulated action.
5. Produce one of: `SIMULATE_BUY`, `SIMULATE_SELL`, `WAIT`, or `CLOSE_SIMULATION`.
6. Store the event in the user-scoped demo ledger.
7. Update the private dashboard and notifications.

The executive must never call `order_send`, the existing execution service, or any route capable of broker execution.

Initial delivery should use the existing short polling model instead of adding WebSockets. This keeps the change smaller and easier to verify. Realtime streaming can be a later enhancement.

## Private Dashboard

The private dashboard keeps the current premium ATLAS visual language and adds:
- Signed-in user identity and logout.
- Plan/access badge.
- MT5 Demo connection state.
- User-scoped account telemetry.
- AI Chart and selected-asset workflow.
- Trend, Momentum, Volatility, Risk, Confidence, and Data Freshness.
- Demo positions and simulated P/L.
- Live Demo Executive status and event timeline.
- Explicit `DEMO` labeling wherever execution-like behavior is shown.
## Security and Trust Requirements

- All private routes require a valid authenticated session.
- User id is derived from the verified session, never accepted from client input.
- Supabase row-level security enforces ownership.
- Service-role secrets, MT5 secrets, and payment secrets stay server-side.
- Session cookies/tokens use secure production settings and are never written to logs.
- Rate-limit login, OTP, connector, and executive-control endpoints.
- Audit authentication, demo-connection state changes, subscription access changes, and executive state changes without storing secrets.
- All user account identifiers remain masked in UI/API payloads unless a protected user-scoped workflow explicitly requires the full value server-side.
- No shared MT5 account telemetry is exposed publicly.
- No promise of returns, no managed-money language, and no real-money execution controls.

## Subscription Integration

Plans are `FREE`, `STARTER`, `PRO`, and `ELITE`. FREE is still a private account: it can authenticate, connect one verified MT5 Demo account, and view only its own read-only Balance, Equity, Open Positions, Pending Orders, Trade History, market context, and AI analysis. Paid plans may add deeper analytics, alerts, longer history, support, and Live Demo Executive capabilities.

No subscription tier enables real-money broker execution.

Existing Whish/manual-review flows can map a verified payment record to the authenticated Supabase user. Stripe support, if retained, should use the same user-id mapping.

## Alternatives Considered

1. Custom username/password auth in FastAPI: rejected because password storage, reset, verification, and OAuth add unnecessary security surface.
2. Google-only login: simpler, but excludes users who prefer email.
3. Supabase Google + Email OTP: selected because it provides both flows, session management, user identity, and database/RLS integration with less custom security code.
## API Shape

Proposed authenticated endpoints:
- `GET /api/me` — current user profile and access state.
- `GET /api/user/dashboard` — user-scoped dashboard payload.
- `GET/PUT /api/user/settings` — language/theme/preferences.
- `POST /api/mt5-demo/connect` — establish a verified DEMO telemetry session.
- `POST /api/mt5-demo/disconnect` — end the demo telemetry session.
- `GET /api/mt5-demo/state` — masked account and connection state.
- `GET /api/demo-executive/status` — current simulation state.
- `POST /api/demo-executive/start` — start user-scoped demo simulation.
- `POST /api/demo-executive/stop` — stop demo simulation.
- `GET /api/demo-executive/events` — recent simulated decisions and context.

The existing shared `/dashboard/atlas` behavior must be retired from public use. User dashboard payloads must come only from authenticated, user-scoped endpoints.

## Rollout Order

1. Supabase Auth and protected-session middleware.
2. Landing-page `Enter ATLAS`, login, callback, logout, and private dashboard shell.
3. User profile/settings persistence and isolation tests.
4. MT5 Demo-only connector with explicit REAL-account rejection.
5. Live Demo Executive simulation ledger and private dashboard controls.
6. Subscription-to-user mapping and plan feature gates.
7. Production deployment, public-route regression checks, and mobile/desktop verification.
## Verification Requirements

Automated tests must prove:
- Unauthenticated users cannot access private dashboard APIs.
- Google/email-authenticated sessions resolve to the correct user.
- User A cannot read or mutate User B data.
- A REAL or unverifiable MT5 account is rejected by the demo connector.
- Demo Executive events are stored only in the requesting user's ledger.
- Starting the Demo Executive cannot reach broker execution code.
- No shared/public MT5 dashboard endpoint exposes account telemetry.
- FREE users can connect one verified MT5 Demo account and see only their own read-only data.
- Existing ATLAS tests remain green.
- Mobile and desktop private-dashboard routes render correctly.

Production checks must verify:
- `/health` returns HTTP 200.
- `/` shows `Enter ATLAS`.
- `/login` loads both Google and email-OTP options.
- `/app/dashboard` redirects unauthenticated visitors to login.
- `/dashboard` requires authentication or redirects to `/login`.
- A FREE user can connect one verified MT5 Demo account and see only that account's read-only telemetry.

## Non-Goals

- Real-money trading or broker order submission.
- Managed accounts or custody of customer funds.
- Guaranteed returns, profit promises, or autonomous investment advice.
- Storing raw broker passwords in application tables.
- Any public/shared MT5 account preview.
- WebSocket infrastructure in the first implementation.

## Success Criteria

The feature is complete when a new user can enter ATLAS with Google or email OTP, receive a private FREE account by default, connect one verified MT5 Demo account, see only that account's read-only telemetry and AI context, and—where their plan permits—run the Live Demo Executive simulation without any broker-order path being reachable.


