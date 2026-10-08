# ATLAS Web App UI/UX Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the existing ATLAS web application into one coherent premium dark/orange desktop-and-mobile experience across preview, login, connect, dashboard, ATLAS AI, news, and all loading/empty/error/locked states.

**Architecture:** Keep the existing Next.js application, API clients, Supabase session flow, and Paper runtime intact. Consolidate presentation behavior in the existing shell/components and shared CSS, extract only small state/status primitives where duplication is real, and verify each flow independently before a rollback-safe production swap.

**Tech Stack:** Next.js 15.5, React 19, TypeScript 5.8, Vitest 3, Testing Library, existing Supabase browser auth integration, existing ATLAS REST APIs.

**Spec:** `docs/superpowers/specs/2026-10-08-atlas-web-app-ui-ux-refinement-design.md`

## Global Constraints

- Keep ATLAS in a Paper-only trading workspace.
- Do not add or expose broker-order execution controls.
- Preserve Google OAuth and email sign-in behavior.
- Preserve the current Supabase-backed private session flow.
- Preserve Arabic and English support.
- Arabic uses RTL; English uses LTR.
- Keep public preview safe for unauthenticated visitors.
- Keep private account and session data behind authentication.
- Reuse existing APIs and data models unless a presentation requirement cannot be met without a small interface change.
- Do not introduce a second parallel design system.
- Display no more than three primary headlines in the dashboard.
- The UI must continue to communicate and enforce `PAPER MODE`, broker execution disabled, and Paper positions/training as simulations.
- Build into a temporary Next build directory, retain the current `.next-production` as rollback, and only swap after verification.

## Execution Prerequisite

The live source directory `runtime/web-ui` is currently untracked by the root Git repository. Before implementation:

1. Restore a worktree-capable Git CLI, or install a portable Git binary without altering application dependencies.
2. Create `runtime/web-ui/.gitignore` so source can be tracked while excluding at minimum:
   - `node_modules/`
   - `.next*/`
   - `coverage/`
   - `.env*`
   - `*.log`
3. Verify no secret-bearing files are staged.
4. Commit the current web-ui source as a baseline commit.
5. Create an isolated Git worktree from that baseline and execute Tasks 1-6 there.
6. Never copy `.runtime/config`, secret files, or production build output into the worktree.

If this prerequisite cannot be completed safely, stop before product-code changes.

## File Structure

- `runtime/web-ui/app/atlas-app-shell.tsx` — live/public workspace state orchestration and top-level authenticated/anonymous presentation.
- `runtime/web-ui/app/login/page.tsx` — login page composition.
- `runtime/web-ui/app/connect/page.tsx` — guided MT5 data-connection page.
- `runtime/web-ui/app/globals.css` — one shared ATLAS visual system and responsive behavior.
- `runtime/web-ui/components/layout/atlas-shell.tsx` — shared desktop/mobile application frame.
- `runtime/web-ui/components/layout/sidebar.tsx` — desktop navigation.
- `runtime/web-ui/components/layout/mobile-nav.tsx` — five-action mobile navigation.
- `runtime/web-ui/components/system/section-state.tsx` — new reusable loading/empty/error/locked presentation primitive.
- `runtime/web-ui/components/system/status-pill.tsx` — new reusable concise status pill primitive.
- `runtime/web-ui/features/auth/private-login.tsx` — Google/email auth controls and user-visible auth states.
- `runtime/web-ui/features/auth/session.ts` — existing safe OAuth URL/session helpers; preserve direct Google authorize behavior.
- `runtime/web-ui/features/dashboard/dashboard-screen.tsx` — dashboard information hierarchy.
- `runtime/web-ui/features/ai/atlas-assistant.tsx` — ATLAS AI visual states and quick prompts.
- `runtime/web-ui/lib/navigation.ts` — desktop navigation source.
- Tests remain under `runtime/web-ui/tests/`.

## Review Focus

1. **Anonymous/private boundary:** a 401 dashboard response must never render balance, insight cards, positions, or enabled ATLAS AI input; Task 4 adds an explicit regression test.
2. **OAuth CDN failure:** Google sign-in must still initiate when the external Supabase browser script is unavailable; Task 2 adds a regression test that withholds `onReady`.
3. **Long bilingual news titles:** long Arabic and English headlines must wrap without horizontal overflow; Task 5 adds rendering/CSS assertions.
4. **RTL/LTR switching:** the workspace must change `dir` while preserving navigation/status meaning and market-number readability; Task 4 adds Arabic/English direction tests.
5. **Small-screen safe area:** five-item navigation must remain usable without covering content on narrow phones and devices with a bottom safe area; Task 6 adds CSS hook assertions and a five-action DOM check.

---

### Task 1: Shared Shell, Navigation, and Visual Primitives

**Files:**
- Create: `runtime/web-ui/components/system/section-state.tsx`
- Create: `runtime/web-ui/components/system/status-pill.tsx`
- Modify: `runtime/web-ui/components/layout/atlas-shell.tsx`
- Modify: `runtime/web-ui/components/layout/sidebar.tsx`
- Modify: `runtime/web-ui/components/layout/mobile-nav.tsx`
- Modify: `runtime/web-ui/lib/navigation.ts`
- Modify: `runtime/web-ui/app/globals.css`
- Test: `runtime/web-ui/tests/navigation.test.tsx`
- Test: `runtime/web-ui/tests/mobile-reference-ui.test.tsx`
- Test: `runtime/web-ui/tests/brand-logo.test.tsx`

**Interfaces:**
- Consumes: existing `AtlasWordmark`, `NAV_ITEMS`, and anchor destinations `#markets`, `#signals`, `#risk`, `#news`, `#ai`.
- Produces: `SectionState({ kind, title, message, action? })`, `StatusPill({ tone, children })`, and a stable shell where mobile navigation defaults to Markets.

- [ ] **Step 1: Write the failing navigation and primitive tests**

Update `navigation.test.tsx` so the mobile labels are exactly:
`["الأسواق", "الإشارات", "المخاطر", "الأخبار", "ATLAS AI"]`.

Assert:
- five mobile links,
- Markets has `aria-current="page"` initially,
- clicking News moves `aria-current` to News,
- desktop navigation still exposes Dashboard, Markets, Trade, Signals, Risk, Analytics, News, ATLAS AI, Account.

Add focused tests for:
- `SectionState` rendering an action only when supplied,
- `StatusPill` exposing the requested tone class.

- [ ] **Step 2: Run tests to verify the stale/default expectations fail**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\navigation.test.tsx tests\mobile-reference-ui.test.tsx tests\brand-logo.test.tsx --reporter=dot --testTimeout=5000`

Expected: FAIL on the old ATLAS-AI-default navigation expectation and/or missing new primitives.

- [ ] **Step 3: Implement the shared shell and primitives**

Implement:
- `SectionState` with `kind: "loading" | "empty" | "error" | "locked"`.
- `StatusPill` with `tone: "paper" | "online" | "warning" | "private"`.
- consistent desktop shell/header spacing,
- five mobile actions in the approved order,
- Markets as mobile default,
- shared focus-visible styling,
- shared card radius/border/shadow tokens in `globals.css`,
- restrained orange accent and dark navy/black surfaces.

Do not introduce route changes.

- [ ] **Step 4: Run Task 1 tests**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/web-ui/components/system/section-state.tsx runtime/web-ui/components/system/status-pill.tsx runtime/web-ui/components/layout/atlas-shell.tsx runtime/web-ui/components/layout/sidebar.tsx runtime/web-ui/components/layout/mobile-nav.tsx runtime/web-ui/lib/navigation.ts runtime/web-ui/app/globals.css runtime/web-ui/tests/navigation.test.tsx runtime/web-ui/tests/mobile-reference-ui.test.tsx runtime/web-ui/tests/brand-logo.test.tsx
git commit -m "feat: unify ATLAS application shell"
```

### Task 2: Login and Authentication UX States

**Files:**
- Modify: `runtime/web-ui/app/login/page.tsx`
- Modify: `runtime/web-ui/features/auth/private-login.tsx`
- Modify: `runtime/web-ui/features/auth/session.ts` only if required to preserve the already-working direct authorize URL
- Modify: `runtime/web-ui/app/globals.css`
- Test: `runtime/web-ui/tests/login.test.tsx`
- Test: `runtime/web-ui/tests/private-login-flow.test.tsx`
- Test: `runtime/web-ui/tests/private-auth.test.ts`
- Test: `runtime/web-ui/tests/brand-logo.test.tsx`

**Interfaces:**
- Consumes: `buildGoogleAuthorizeUrl(origin, supabaseUrl, returnTo)`, `createBackendSession(token)`, `safeReturnTo(raw)`.
- Produces: a primary Google sign-in that becomes usable as soon as auth config is loaded, independent of the external Supabase browser bundle; email/callback behavior remains unchanged.
- Produces: `data-auth-state="loading" | "ready" | "busy" | "success" | "error"` on the `PrivateLogin` root for consistent styling/testing.

- [ ] **Step 1: Add failing auth-state tests**

In `private-login-flow.test.tsx`, add:
- auth config resolves,
- mocked `next/script` never calls `onReady`,
- `Continue with Google` is enabled,
- the root reports `data-auth-state="ready"` before the external script is ready,
- clicking Google moves the root to `data-auth-state="busy"` and attempts navigation to the project `/auth/v1/authorize?provider=google...` URL.

In `login.test.tsx`, assert:
- Paper-only copy remains visible,
- Google remains the primary button,
- email remains secondary,
- status region remains present.

- [ ] **Step 2: Run auth tests to verify failure**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\login.test.tsx tests\private-login-flow.test.tsx tests\private-auth.test.ts tests\brand-logo.test.tsx --reporter=dot --testTimeout=5000`

Expected: FAIL because the current `PrivateLogin` root does not expose the new `data-auth-state` contract.

- [ ] **Step 3: Implement login refinement**

Keep:
- direct Google authorize URL behavior,
- email magic link,
- callback exchange into backend session.

Refine:
- map loading, opening-Google/email-send, signed-in, and error conditions to the exact `data-auth-state` values defined above,
- loading, opening-Google, email-sent, signed-in, and error states using shared state/status styling,
- two-column desktop and single-column mobile hierarchy,
- concise Paper-only/privacy copy,
- no dependency on external script readiness for initiating Google OAuth.

- [ ] **Step 4: Run auth tests**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/web-ui/app/login/page.tsx runtime/web-ui/features/auth/private-login.tsx runtime/web-ui/features/auth/session.ts runtime/web-ui/app/globals.css runtime/web-ui/tests/login.test.tsx runtime/web-ui/tests/private-login-flow.test.tsx runtime/web-ui/tests/private-auth.test.ts runtime/web-ui/tests/brand-logo.test.tsx
git commit -m "feat: refine ATLAS secure sign in"
```

### Task 3: Guided Connect Experience

**Files:**
- Modify: `runtime/web-ui/app/connect/page.tsx`
- Modify: `runtime/web-ui/features/trades/account-connection.tsx` only for presentation/state hooks, not connection semantics
- Modify: `runtime/web-ui/app/globals.css`
- Create: `runtime/web-ui/tests/connect-page.test.tsx`

**Interfaces:**
- Consumes: `/api/me`, `/api/mt5-demo/state`, owner-only `/api/runtime/status`, and existing `AccountConnection`.
- Produces: a guided Connect page with explicit signed-out, disconnected, connected, owner-runtime, and Paper-only states.

- [ ] **Step 1: Write failing Connect tests**

Create `connect-page.test.tsx` covering:
- anonymous `/api/me` failure shows Sign in and does not show runtime toggle,
- signed-in disconnected state shows the MT5 connection card and Paper-only explanation,
- owner state with runtime data shows learned-council status,
- non-owner state never shows owner runtime controls,
- the page exposes Dashboard and Subscription links.

- [ ] **Step 2: Run Connect tests to verify failure**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\connect-page.test.tsx --reporter=dot --testTimeout=5000`

Expected: FAIL because the new guided structure/test hooks do not yet exist.

- [ ] **Step 3: Implement the guided Connect layout**

Structure the page as:
1. page header/status,
2. authentication gate,
3. MT5 data connection,
4. connection/council status,
5. Paper-only safety note,
6. Dashboard/Subscription actions.

Use `SectionState` and `StatusPill` from Task 1. Do not change endpoint semantics and do not expose live broker execution.

- [ ] **Step 4: Run Connect tests**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/web-ui/app/connect/page.tsx runtime/web-ui/features/trades/account-connection.tsx runtime/web-ui/app/globals.css runtime/web-ui/tests/connect-page.test.tsx
git commit -m "feat: guide ATLAS account connection"
```

### Task 4: Dashboard Hierarchy and Public/Private Safety

**Files:**
- Modify: `runtime/web-ui/app/atlas-app-shell.tsx`
- Modify: `runtime/web-ui/features/dashboard/dashboard-screen.tsx`
- Modify: `runtime/web-ui/app/globals.css`
- Test: `runtime/web-ui/tests/live-shell.test.tsx`
- Test: `runtime/web-ui/tests/dashboard-screen.test.tsx`

**Interfaces:**
- Consumes: `DashboardViewModel`, chart candles, headlines, session-required state, existing market/signal/risk/activity panels.
- Produces: four-level dashboard hierarchy: orientation, decision surface, ATLAS AI, monitoring; anonymous mode remains read-only and private values remain hidden.

- [ ] **Step 1: Add failing hierarchy/safety tests**

In `live-shell.test.tsx`, extend the anonymous 401 case to assert:
- no balance value,
- no insight grid,
- no enabled ATLAS AI textbox,
- sign-in action remains present,
- the public preview hero exposes the ATLAS Paper-intelligence identity and clear Sign in / Connect actions.

Add a language test that renders Arabic then English and asserts workspace `dir="rtl"` then `dir="ltr"`.

In `dashboard-screen.test.tsx`, assert explicit test IDs/order hooks for:
- orientation,
- decision surface,
- ATLAS AI,
- monitoring.

- [ ] **Step 2: Run dashboard tests to verify failure**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\live-shell.test.tsx tests\dashboard-screen.test.tsx --reporter=dot --testTimeout=5000`

Expected: FAIL on the new hierarchy/direction hooks.

- [ ] **Step 3: Implement dashboard hierarchy**

Refine:
- compact top orientation/status area,
- a deliberate public-preview hero with ATLAS identity plus Sign in / Connect actions,
- Paper Mode, private/owner, MT5 data status,
- chart-first decision surface,
- insight/stat strips,
- ATLAS AI as a primary section,
- monitoring sections below,
- public preview gate that never leaks private account/session data,
- dashboard loading/error/locked placeholders migrated to `SectionState` where the state maps cleanly.

Keep all existing Paper-only safety logic.

- [ ] **Step 4: Run dashboard tests**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/web-ui/app/atlas-app-shell.tsx runtime/web-ui/features/dashboard/dashboard-screen.tsx runtime/web-ui/app/globals.css runtime/web-ui/tests/live-shell.test.tsx runtime/web-ui/tests/dashboard-screen.test.tsx
git commit -m "feat: clarify ATLAS dashboard hierarchy"
```

### Task 5: ATLAS AI and Three-Headline News Experience

**Files:**
- Modify: `runtime/web-ui/features/ai/atlas-assistant.tsx`
- Modify: `runtime/web-ui/features/dashboard/dashboard-screen.tsx`
- Modify: `runtime/web-ui/app/globals.css`
- Test: `runtime/web-ui/tests/atlas-assistant.test.tsx`
- Test: `runtime/web-ui/tests/dashboard-screen.test.tsx`
- Test: `runtime/web-ui/tests/briefing.test.ts`

**Interfaces:**
- Consumes: `sendMessage({ message })`, current `Headline[]`, existing lock URL.
- Produces: `AtlasAssistant` prop `quickPrompts?: readonly string[]`; quick prompts populate the input but do not auto-send.

- [ ] **Step 1: Write failing ATLAS AI/news tests**

Add ATLAS AI tests:
- quick prompts render,
- clicking a quick prompt fills the textbox,
- locked state keeps quick prompts non-operative and retains Sign in/Activate action,
- send/error behavior remains unchanged.

Add dashboard/news tests:
- only three headlines render when four are provided,
- long Arabic and English headline fixtures render as links,
- CSS contains `overflow-wrap: anywhere` or equivalent on headline link text.

- [ ] **Step 2: Run AI/news tests to verify failure**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\atlas-assistant.test.tsx tests\dashboard-screen.test.tsx tests\briefing.test.ts --reporter=dot --testTimeout=5000`

Expected: FAIL on missing quick-prompt behavior and long-headline styling assertion.

- [ ] **Step 3: Implement ATLAS AI and news refinement**

Implement:
- `quickPrompts?: readonly string[]`,
- localized default prompts from `DashboardScreen` such as analyze selected market, check risk levels, summarize market news,
- prompt click fills input without sending,
- clear ready/sending/error/locked visual states aligned with the shared state system,
- news unavailable/empty states rendered through `SectionState`,
- news cards/rows with headline, source, optional time only when data already supplies it,
- maximum three rendered headlines,
- robust wrapping.

Do not add new backend AI or news endpoints.

- [ ] **Step 4: Run AI/news tests**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/web-ui/features/ai/atlas-assistant.tsx runtime/web-ui/features/dashboard/dashboard-screen.tsx runtime/web-ui/app/globals.css runtime/web-ui/tests/atlas-assistant.test.tsx runtime/web-ui/tests/dashboard-screen.test.tsx runtime/web-ui/tests/briefing.test.ts
git commit -m "feat: elevate ATLAS AI and market news"
```

### Task 6: Responsive, Accessibility, and State-System Integration

**Files:**
- Modify: `runtime/web-ui/app/globals.css`
- Modify: `runtime/web-ui/components/system/section-state.tsx`
- Modify: `runtime/web-ui/components/layout/mobile-nav.tsx` only if integration reveals a missing hook
- Create: `runtime/web-ui/tests/ui-system.test.tsx`
- Test: `runtime/web-ui/tests/navigation.test.tsx`
- Test: `runtime/web-ui/tests/mobile-reference-ui.test.tsx`

**Interfaces:**
- Consumes: Task 1 shell/state primitives and all page classes added in Tasks 2-5.
- Produces: consistent focus, safe-area, reduced-motion, mobile-width, and state-system behavior across the web app.

- [ ] **Step 1: Write failing UI-system tests**

Create `ui-system.test.tsx` that reads `globals.css` and asserts:
- `:focus-visible` styling exists,
- `@media (prefers-reduced-motion: reduce)` exists,
- `env(safe-area-inset-bottom)` is used for mobile navigation spacing,
- narrow-screen rules prevent horizontal overflow on the app shell,
- news link wrapping rule exists,
- shared loading/empty/error/locked state classes exist.

Keep the DOM assertion that mobile nav has exactly five actions.

- [ ] **Step 2: Run integration tests to verify failure**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\ui-system.test.tsx tests\navigation.test.tsx tests\mobile-reference-ui.test.tsx --reporter=dot --testTimeout=5000`

Expected: FAIL on one or more missing integration hooks.

- [ ] **Step 3: Implement responsive/accessibility integration**

Add:
- visible keyboard focus,
- reduced-motion handling for nonessential animation,
- safe-area mobile bottom spacing,
- no horizontal overflow at narrow widths,
- consistent touch target minimums,
- shared state classes,
- RTL/LTR-safe alignment,
- responsive desktop-to-mobile card/grid collapse.

- [ ] **Step 4: Run all relevant frontend tests**

Run:
`node .\node_modules\vitest\vitest.mjs run tests\navigation.test.tsx tests\mobile-reference-ui.test.tsx tests\brand-logo.test.tsx tests\login.test.tsx tests\private-login-flow.test.tsx tests\private-auth.test.ts tests\connect-page.test.tsx tests\live-shell.test.tsx tests\dashboard-screen.test.tsx tests\atlas-assistant.test.tsx tests\briefing.test.ts tests\ui-system.test.tsx --reporter=dot --testTimeout=5000`

Expected: PASS.

- [ ] **Step 5: Run production build**

From `runtime/web-ui`:

```powershell
Remove-Item '.next-uiux-final' -Recurse -Force -ErrorAction SilentlyContinue
$env:ATLAS_BACKEND_ORIGIN='http://127.0.0.1:8012'
$env:ATLAS_BUILD_DIR='.next-uiux-final'
$env:NEXT_TELEMETRY_DISABLED='1'
node '.\node_modules\next\dist\bin\next' build
```

Expected:
- compile success,
- type check success,
- static page generation completes,
- process exit code 0.

Remove the temporary `.next-uiux-final/types/**/*.ts` include from `tsconfig.json` if Next adds it.

- [ ] **Step 6: Commit**

```bash
git add runtime/web-ui/app/globals.css runtime/web-ui/components/system/section-state.tsx runtime/web-ui/components/layout/mobile-nav.tsx runtime/web-ui/tests/ui-system.test.tsx runtime/web-ui/tests/navigation.test.tsx runtime/web-ui/tests/mobile-reference-ui.test.tsx runtime/web-ui/tsconfig.json
git commit -m "feat: finish ATLAS responsive UI system"
```

### Task 7: Production Rollout and Live Verification

**Files:**
- No source-file changes expected.
- Production build input: `runtime/web-ui/.next-uiux-final`
- Production build target: `runtime/web-ui/.next-production`

**Interfaces:**
- Consumes: validated Task 6 build.
- Produces: live `https://justai-atlas.online` serving the approved UI/UX with rollback build retained.

- [ ] **Step 1: Verify runtime tasks before deployment**

Check:
- `ATLAS Private Backend` = Running,
- `ATLAS Web Frontend` = Running,
- `ATLAS Paper Monitor` = Running,
- `http://127.0.0.1:8012/health` = 200 healthy.

Expected: all healthy before swap.

- [ ] **Step 2: Swap the validated frontend build**

Stop only `ATLAS Web Frontend`.

Rename current `.next-production` to timestamped `.next-production-prev-<timestamp>`.

Rename `.next-uiux-final` to `.next-production`.

Restart `ATLAS Web Frontend`.

Expected: task returns Running.

- [ ] **Step 3: Local smoke tests**

Verify HTTP 200:
- `http://127.0.0.1:8011/`
- `http://127.0.0.1:8011/login`
- `http://127.0.0.1:8011/connect`
- `http://127.0.0.1:8011/dashboard`
- `http://127.0.0.1:8011/backend/health`

Expected: all 200.

- [ ] **Step 4: Public smoke tests**

Verify HTTP 200:
- `https://justai-atlas.online/`
- `https://justai-atlas.online/login`
- `https://justai-atlas.online/connect`
- `https://justai-atlas.online/dashboard`
- `https://justai-atlas.online/backend/health`

Verify public news endpoint returns at most three headlines for Arabic and English.

Expected: all healthy.

- [ ] **Step 5: Verify Google OAuth initiation**

From the live login page, click `Continue with Google`.

Expected:
- navigation reaches `accounts.google.com`,
- no `invalid_client`,
- no authorization error,
- do not require completing personal account selection for this smoke test.

- [ ] **Step 6: Visual verification**

Review:
- desktop width around 1440px,
- mobile width around 390px,
- Arabic RTL,
- English LTR,
- login,
- connect,
- dashboard,
- ATLAS AI locked and ready presentation,
- three-news layout,
- mobile five-action navigation,
- no horizontal overflow,
- no broker execution controls.

Expected: visual structure matches the approved concept direction and spec.

- [ ] **Step 7: Verify Paper runtime remained untouched**

Confirm:
- `ATLAS Paper Monitor` remains Running,
- runtime config remains `ATLAS_LIVE_TRADING=false`,
- environment remains `paper`,
- broker execution remains disabled,
- Paper state files continue updating.

Expected: UI deployment did not change trading runtime safety.

## Completion Contract

The plan is complete only when:
- every Task 1-6 test command passes,
- production Next build exits 0,
- Task 7 local/public smoke tests pass,
- Google OAuth initiation reaches Google without `invalid_client`,
- desktop/mobile Arabic/English visual checks pass,
- Paper-only safety remains intact,
- a timestamped rollback build exists.
