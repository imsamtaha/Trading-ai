# ATLAS Private Multi-User Auth + MT5 Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ATLAS private-by-default so every user authenticates, receives an isolated account, and can connect one verified MT5 Demo account for read-only telemetry; paid tiers may additionally use the Live Demo Executive simulation.

**Architecture:** Supabase Auth supplies Google + email OTP identity. FastAPI derives `user_id` only from verified sessions and exposes user-scoped APIs backed by Supabase/RLS; the MT5 connector is DEMO-only and read-only, while the Live Demo Executive writes only simulated user-scoped events and can never reach broker order submission.

**Tech Stack:** Python 3.13, FastAPI, Supabase Auth/Postgres/RLS, existing MT5 adapter, vanilla HTML/JS dashboard, pytest/httpx.

**Spec:** `docs/superpowers/specs/2026-09-26-atlas-auth-user-dashboard-live-demo-executive-design.md`

## Global Constraints

- No public/shared MT5 account telemetry.
- FREE users authenticate and may connect one verified MT5 Demo account read-only.
- REAL/UNKNOWN MT5 accounts are rejected by the connector.
- `ATLAS_LIVE_TRADING=false`; no broker order path may be reachable from user routes.
- User identity is derived from the verified session, never accepted from client input.
- Every persistent record is keyed by authenticated user id and protected by RLS.
- Never log or return Supabase service-role secrets, MT5 passwords, or payment secrets.

## Review Focus

- Expired/invalid Supabase token must fail closed and never fall back to anonymous/shared data.
- User A requesting User B resources must receive no data and no mutation effect.
- MT5 connector must reject REAL, CONTEST, UNKNOWN, or unverifiable accounts.
- Connector failure/reconnect must not leak one user's prior account state into another session.
- Live Demo Executive must remain simulation-only even when existing execution modules are importable.

---## File Structure

- Create `app/auth/supabase_auth.py` — token verification and `AuthenticatedUser` model.
- Create `app/auth/routes.py` — login/callback/logout/session endpoints and login page route wiring.
- Create `app/auth/__init__.py` — auth router export.
- Create `app/users/repository.py` — user-scoped profile/settings/subscription/MT5 metadata persistence.
- Create `app/users/routes.py` — `/api/me`, settings, and user dashboard APIs.
- Create `app/users/__init__.py` — user router export.
- Create `app/mt5_demo/service.py` — DEMO-only read-only connector abstraction.
- Create `app/mt5_demo/routes.py` — user-scoped connect/disconnect/state APIs.
- Create `app/mt5_demo/__init__.py` — MT5 demo router export.
- Create `app/demo_executive/service.py` — simulation-only decision/event service.
- Create `app/demo_executive/routes.py` — status/start/stop/events APIs.
- Create `app/demo_executive/__init__.py` — executive router export.
- Modify `app/dashboard/views.py` — private login-aware dashboard shell and MT5 connection/activity UI.
- Modify `app/dashboard/preferences.py` — bilingual labels for auth/private dashboard/free tier.
- Modify `app/main.py` — include new routers and replace shared dashboard access with auth redirects/protected APIs.
- Modify `requirements.txt` — add only the Supabase/JWT dependency actually used by implementation.
- Create `supabase/migrations/20260926_private_multiuser.sql` — tables + RLS policies.
- Create auth/isolation/MT5/executive tests under `tests/`.

### Task 1: Supabase Session Verification

**Files:**
- Create: `app/auth/supabase_auth.py`
- Test: `tests/test_auth_session.py`

**Interfaces:**
- Produces: `AuthenticatedUser(user_id: str, email: str | None)` and `require_user(request: Request) -> AuthenticatedUser`.

- [ ] Write failing tests proving missing, expired, and invalid tokens return 401 and a valid token resolves the expected user id.
- [ ] Run `python -m pytest tests/test_auth_session.py -q` and verify RED for missing implementation.
- [ ] Implement minimal Supabase token verification using configured project/JWT data; fail closed on verification/config errors.
- [ ] Run the auth tests and verify PASS.
- [ ] Commit `feat: verify ATLAS user sessions`.

### Task 2: Login, Callback, Logout, and Protected Dashboard

**Files:**
- Create: `app/auth/routes.py`, `app/auth/__init__.py`
- Modify: `app/main.py`, `app/dashboard/views.py`, `app/dashboard/preferences.py`
- Test: `tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `require_user()` from Task 1.
- Produces: `/login`, auth callback/session flow, `/logout`, and protected `/dashboard` + `/app/dashboard` behavior.

- [ ] Write failing tests for Google + email OTP UI, unauthenticated dashboard redirect, and authenticated private dashboard access.
- [ ] Run targeted tests and verify RED.
- [ ] Implement routes and private dashboard entry; `/` remains telemetry-free landing page.
- [ ] Run targeted tests and verify PASS.
- [ ] Commit `feat: add private ATLAS login flow`.
### Task 3: User Records, FREE Tier, and RLS Isolation

**Files:**
- Create: `app/users/repository.py`, `app/users/routes.py`, `app/users/__init__.py`
- Create: `supabase/migrations/20260926_private_multiuser.sql`
- Test: `tests/test_user_isolation.py`

**Interfaces:**
- Consumes: authenticated `user_id` from Task 1.
- Produces: `get_or_create_profile(user_id)`, `get_user_settings(user_id)`, `update_user_settings(user_id, payload)`, `get_subscription(user_id)`.

- [ ] Write failing tests proving new users default to `FREE`, User A cannot read/write User B data, and client-supplied user ids are ignored.
- [ ] Run `python -m pytest tests/test_user_isolation.py -q` and verify RED.
- [ ] Add tables for profiles, settings, subscriptions, MT5 metadata, demo positions, and executive events with ownership policies.
- [ ] Implement user repository/routes using only session-derived ids.
- [ ] Run isolation tests and verify PASS.
- [ ] Commit `feat: isolate ATLAS user data with free tier`.

### Task 4: DEMO-Only MT5 Connector

**Files:**
- Create: `app/mt5_demo/service.py`, `app/mt5_demo/routes.py`, `app/mt5_demo/__init__.py`
- Test: `tests/test_user_mt5_demo_connector.py`

**Interfaces:**
- Produces: `connect_demo(user_id, credentials)`, `disconnect_demo(user_id)`, `get_demo_state(user_id)`.
- [ ] Write failing tests for DEMO acceptance, REAL/CONTEST/UNKNOWN rejection, masked metadata, and reconnect isolation between users.
- [ ] Run targeted connector tests and verify RED.
- [ ] Implement a read-only connector that never calls `order_send` and never persists raw passwords.
- [ ] Persist only masked account metadata and connection state keyed by `user_id`.
- [ ] Run targeted tests and verify PASS.
- [ ] Commit `feat: add isolated MT5 demo connections`.

### Task 5: User-Scoped Dashboard Payload

**Files:**
- Modify: `app/users/routes.py`, `app/dashboard/views.py`, `app/dashboard/preferences.py`
- Test: `tests/test_private_dashboard_payload.py`

**Interfaces:**
- Consumes: authenticated user, user repository, and `get_demo_state(user_id)`.
- Produces: `GET /api/user/dashboard` with only the requesting user's Balance, Equity, Open, Pending, History, and AI context.

- [ ] Write failing tests proving FREE users see only their own MT5 Demo telemetry and another user's account never appears.
- [ ] Run targeted tests and verify RED.
- [ ] Implement the user-scoped payload and replace shared `/dashboard/atlas` consumption in the private UI.
- [ ] Add FREE badge, MT5 connection state, Open/Pending/History tabs, and account badge.
- [ ] Run targeted tests and verify PASS.
- [ ] Commit `feat: serve private user dashboard telemetry`.
### Task 6: Live Demo Executive Simulation

**Files:**
- Create: `app/demo_executive/service.py`, `app/demo_executive/routes.py`, `app/demo_executive/__init__.py`
- Test: `tests/test_demo_executive_isolation.py`

**Interfaces:**
- Consumes: authenticated user, user-scoped MT5 Demo state, existing ATLAS analysis/risk helpers.
- Produces: `start(user_id)`, `stop(user_id)`, `status(user_id)`, `events(user_id)` and simulation events only.

- [ ] Write failing tests proving events are user-scoped, FREE access rules are enforced, and no execution module/order function is invoked.
- [ ] Run targeted tests and verify RED.
- [ ] Implement simulation decisions `SIMULATE_BUY`, `SIMULATE_SELL`, `WAIT`, `CLOSE_SIMULATION` with deterministic risk checks.
- [ ] Persist user-scoped events without broker order submission.
- [ ] Run targeted tests and verify PASS.
- [ ] Commit `feat: add private live demo executive`.

### Task 7: Plan Gates and Private Navigation

**Files:**
- Modify: `app/subscription.py`, `app/billing/routes.py`, `app/users/routes.py`, `app/dashboard/views.py`
- Test: `tests/test_private_plan_access.py`

**Interfaces:**
- Consumes: `FREE|STARTER|PRO|ELITE` subscription state.
- Produces: private feature gates without changing the DEMO-only broker boundary.

- [ ] Write failing tests for FREE defaults, paid-feature gating, and no plan enabling broker execution.
- [ ] Run targeted tests and verify RED.
- [ ] Implement plan mapping and private navigation states.
- [ ] Run targeted tests and verify PASS.
- [ ] Commit `feat: gate private ATLAS features by plan`.
### Task 8: Full Regression, Security Checks, and Deployment

**Files:**
- Modify only files required by defects found during verification.
- Test: existing suite + new auth/isolation/MT5/executive tests.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: deployable private multi-user ATLAS build.

- [ ] Run the complete suite: `python -m pytest -q`; require zero failures.
- [ ] Run `git diff --check` and secret scan; require clean results and no credentials in tracked files.
- [ ] Verify `/health` = 200, `/` contains no MT5 telemetry, `/login` exposes Google + email OTP, and unauthenticated `/dashboard` redirects to login.
- [ ] Verify two test users cannot see each other's profile, MT5 metadata, positions, pending orders, history, settings, or executive events.
- [ ] Verify a FREE user can connect exactly one verified MT5 Demo account read-only.
- [ ] Verify REAL/CONTEST/UNKNOWN account connection attempts are rejected.
- [ ] Verify Live Demo Executive cannot call broker execution even when execution modules are present.
- [ ] Deploy with `ATLAS_LIVE_TRADING=false` and retain Cloudflare/health checks.
- [ ] Verify mobile and desktop private dashboard rendering.
- [ ] Commit any verification fixes separately, then push the implementation branch.

## Self-Review Result

- Spec coverage: Auth, private routing, FREE tier, RLS isolation, MT5 Demo-only connection, private dashboard, Live Demo Executive simulation, subscription gates, and deployment are covered.
- Type/interface consistency: later tasks consume session-derived `user_id` and the MT5/user repository interfaces defined earlier.
- Review focus: invalid auth, cross-user access, non-DEMO accounts, reconnect leakage, and broker-execution reachability each have explicit tests.
- Scope boundary: real-money execution, shared MT5 telemetry, and public user dashboards remain excluded.
