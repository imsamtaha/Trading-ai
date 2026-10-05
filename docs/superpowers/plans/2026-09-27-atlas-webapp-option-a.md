# ATLAS Web App Option A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the official responsive ATLAS web application inside `Trading-ai`, preserving the existing FastAPI/MT5/risk/agent backend and adding a production-ready Next.js frontend under `web/`.

**Architecture:** Keep Python/FastAPI as the source of truth for account, market, risk, agent, and execution state. Add a separate typed Next.js frontend in the same repository, with a thin API adapter that maps existing backend responses into UI view models; no trading or risk authorization logic moves into the browser. The existing server-rendered dashboard remains available during migration until the new web build is verified and deployment routing is explicitly switched.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, React Testing Library, Vitest, TradingView Lightweight Charts, existing FastAPI backend, existing pytest suite.

**Spec:** `docs/superpowers/specs/2026-09-27-atlas-webapp-option-a-design.md`

## Global Constraints

- Frontend lives under `web/` in the existing `imsamtaha/Trading-ai` repository.
- Existing Python backend remains authoritative for MT5, execution, account state, risk, and agents.
- UI must not calculate or override backend risk authorization.
- Broker credentials and secrets must never be stored in client-side code.
- Execution requests must remain auditable and must clearly report failure vs success.
- Mobile layout must closely preserve the approved stacked phone concept; desktop must use a professional sidebar workspace.
- Visual palette: near-black/graphite, off-white/metallic text, vivid ATLAS orange, restrained green, amber/orange warnings, limited cool-blue AI accents.
- V1 must not add strategy marketplace, social trading, custom scripting, broker marketplace, billing redesign, tax reporting, or a native mobile app.
- Existing backend tests must remain passing.

## Review Focus

- Backend unavailable or partially unavailable: UI must show explicit offline/error states rather than stale success.
- Missing/nullable account and risk fields: UI must render safe placeholders without crashing or inventing values.
- Malformed or empty candle series: chart shell must stay usable and explain that market data is unavailable.
- Mobile viewport overflow: core cards, chart, navigation, and assistant must remain usable at narrow phone widths.
- Public browser bundle inspection: no broker credentials, API secrets, authorization headers, or owner-only execution tokens may be embedded.

---

### Task 1: Scaffold the isolated web application and test harness

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/postcss.config.mjs`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/globals.css`
- Create: `web/vitest.config.ts`
- Create: `web/tests/setup.ts`
- Create: `web/tests/app-shell.test.tsx`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: no new internal interfaces.
- Produces: runnable `web/` app with scripts `dev`, `build`, `lint`, `test`; root React component `AtlasAppShell` rendered by `web/app/page.tsx`.

- [ ] **Step 1: Write the failing shell test**

Create `web/tests/app-shell.test.tsx` asserting that the initial page renders visible text `ATLAS`, `Trading Intelligence`, and an element with `data-testid="atlas-app-shell"`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npm test -- --run tests/app-shell.test.tsx`

Expected: FAIL because the app scaffold/component does not exist yet.

- [ ] **Step 3: Implement the minimal Next.js/TypeScript/Tailwind/Vitest scaffold**

Create the files above, define `AtlasAppShell(): JSX.Element`, and render the required brand text without business data or backend calls.

- [ ] **Step 4: Verify tests and build**

Run: `cd web && npm test -- --run tests/app-shell.test.tsx && npm run build && npm run lint`

Expected: all commands PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore web
git commit -m "feat(web): scaffold ATLAS frontend"
```

### Task 2: Implement ATLAS visual tokens and responsive navigation shell

**Files:**
- Create: `web/components/layout/atlas-shell.tsx`
- Create: `web/components/layout/sidebar.tsx`
- Create: `web/components/layout/mobile-nav.tsx`
- Create: `web/components/brand/atlas-wordmark.tsx`
- Create: `web/lib/navigation.ts`
- Modify: `web/app/page.tsx`
- Modify: `web/app/globals.css`
- Create: `web/tests/navigation.test.tsx`

**Interfaces:**
- Consumes: `AtlasAppShell` from Task 1.
- Produces: `NAV_ITEMS: readonly NavItem[]`, `Sidebar()`, `MobileNav()`, `AtlasWordmark()`, responsive shell regions keyed by destinations `dashboard|markets|trade|signals|risk|analytics|news|ai|account`.

- [ ] **Step 1: Write failing responsive navigation tests**

Assert all nine navigation labels exist, desktop sidebar has `data-testid="desktop-sidebar"`, mobile nav has `data-testid="mobile-nav"`, and active destination uses `aria-current="page"`.

- [ ] **Step 2: Run the navigation test**

Run: `cd web && npm test -- --run tests/navigation.test.tsx`

Expected: FAIL because layout components are missing.

- [ ] **Step 3: Implement the ATLAS shell and visual tokens**

Define CSS variables for graphite background/surfaces, off-white text, ATLAS orange, restrained green, warning amber, and cool-blue AI accent. Implement sidebar for desktop and fixed bottom navigation for narrow screens; ensure only CSS/responsive behavior changes presentation, not route semantics.

- [ ] **Step 4: Verify navigation and phone-width rendering contract**

Run: `cd web && npm test -- --run tests/navigation.test.tsx && npm run build`

Expected: PASS; no horizontal overflow introduced by shell CSS at the component level.

- [ ] **Step 5: Commit**

```bash
git add web/components web/lib/navigation.ts web/app
git commit -m "feat(web): add ATLAS responsive shell"
```

### Task 3: Add typed backend API client and safe state mapping

**Files:**
- Create: `web/lib/api/types.ts`
- Create: `web/lib/api/client.ts`
- Create: `web/lib/api/dashboard.ts`
- Create: `web/lib/api/market.ts`
- Create: `web/lib/api/agent.ts`
- Create: `web/lib/api/mappers.ts`
- Create: `web/lib/api/fixtures.ts`
- Create: `web/tests/api-mappers.test.ts`
- Create: `web/tests/api-client.test.ts`

**Interfaces:**
- Consumes: existing backend routes including `/health`, `/api`, `/mt5/cockpit-state`, `/dashboard/mt5-state`, `/dashboard/market-briefing`, `/market/{symbol}`, `/market/{symbol}/candles`, `/mt5/positions`, and `/agent/right-hand/chat` where available.
- Produces: `getDashboardState(): Promise<DashboardViewModel>`, `getCandles(symbol: string, interval: string, limit?: number): Promise<Candle[]>`, `getPositions(): Promise<Position[]>`, `sendAgentMessage(input: AgentChatRequest): Promise<AgentChatResponse>`, and pure mapper functions that tolerate missing/nullable fields.

- [ ] **Step 1: Write failing mapper tests**

Cover complete account data, missing equity/P&L values, missing risk object, empty positions, and malformed candle entries. Assertions must require placeholders/null-safe values rather than fabricated market/account data.

- [ ] **Step 2: Run mapper tests**

Run: `cd web && npm test -- --run tests/api-mappers.test.ts`

Expected: FAIL because types/mappers do not exist.

- [ ] **Step 3: Implement typed DTOs and pure mappers**

Define backend-facing DTOs separately from UI view models. Map absent numeric values to `null`, absent connection state to `unknown`, and skip malformed candle points rather than crashing.

- [ ] **Step 4: Write and run API client failure-state tests**

Mock `fetch` for HTTP 503, invalid JSON, timeout/abort, and success. `AtlasApiError` must preserve endpoint and status; no failed request may resolve as a success object.

Run: `cd web && npm test -- --run tests/api-client.test.ts`

Expected after implementation: PASS.

- [ ] **Step 5: Verify no secret-bearing defaults**

Run: `cd web && grep -R "OPENAI_API_KEY\|MT5_PASSWORD\|authorization" app components lib --exclude-dir=node_modules || true`

Expected: no embedded secret values and no hard-coded owner execution authorization token.

- [ ] **Step 6: Commit**

```bash
git add web/lib/api web/tests/api-*.test.ts
git commit -m "feat(web): add typed ATLAS API adapter"
```

### Task 4: Build dashboard account, market, and risk cockpit cards

**Files:**
- Create: `web/features/dashboard/dashboard-screen.tsx`
- Create: `web/features/dashboard/account-card.tsx`
- Create: `web/features/dashboard/stat-card.tsx`
- Create: `web/features/markets/market-tile.tsx`
- Create: `web/features/risk/risk-panel.tsx`
- Create: `web/features/activity/activity-panel.tsx`
- Modify: `web/app/page.tsx`
- Create: `web/tests/dashboard-screen.test.tsx`
- Create: `web/tests/risk-panel.test.tsx`

**Interfaces:**
- Consumes: `DashboardViewModel` and market/risk models from Task 3.
- Produces: `DashboardScreen({state}: {state: DashboardViewModel})`, reusable account/stat/market/risk/activity cards, and explicit `loading|offline|ready|error` visual states.

- [ ] **Step 1: Write failing dashboard tests**

Assert rendering of account mode/status, balance, equity, floating P/L, daily P/L, risk level, market tiles, and explicit offline placeholders when backend state is unavailable.

- [ ] **Step 2: Run dashboard tests**

Run: `cd web && npm test -- --run tests/dashboard-screen.test.tsx tests/risk-panel.test.tsx`

Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement the responsive cockpit cards**

Match the approved dark graphite/orange design with compact financial typography, rounded cards, restrained glow, and stacked mobile order. Risk panel must render overall risk, daily loss usage, drawdown, exposure, position-size utilization, aggregate open risk, warnings, and protection state only from mapped backend data.

- [ ] **Step 4: Verify null/offline behavior and build**

Run: `cd web && npm test -- --run tests/dashboard-screen.test.tsx tests/risk-panel.test.tsx && npm run build`

Expected: PASS with no crash on missing fields.

- [ ] **Step 5: Commit**

```bash
git add web/features web/app/page.tsx web/tests/dashboard-screen.test.tsx web/tests/risk-panel.test.tsx
git commit -m "feat(web): build ATLAS dashboard cockpit"
```

### Task 5: Add interactive trading chart and market workspace

**Files:**
- Create: `web/features/chart/trading-chart.tsx`
- Create: `web/features/chart/chart-toolbar.tsx`
- Create: `web/features/chart/chart-overlays.ts`
- Create: `web/features/markets/market-workspace.tsx`
- Create: `web/tests/chart-overlays.test.ts`
- Create: `web/tests/market-workspace.test.tsx`
- Modify: `web/package.json`

**Interfaces:**
- Consumes: `Candle[]`, symbol/timeframe API functions from Task 3.
- Produces: `TradingChart({candles, signals, levels, symbol, timeframe})`, `MarketWorkspace`, overlay converter functions for signal markers and entry/SL/TP price lines.

- [ ] **Step 1: Write failing chart data/overlay tests**

Assert valid candles map to ascending chart points, malformed/duplicate timestamps are filtered deterministically, empty series returns an empty safe dataset, and provided entry/SL/TP levels map to labeled price lines.

- [ ] **Step 2: Run chart tests**

Run: `cd web && npm test -- --run tests/chart-overlays.test.ts tests/market-workspace.test.tsx`

Expected: FAIL because chart modules do not exist.

- [ ] **Step 3: Add Lightweight Charts and implement the chart client component**

Support symbol switching, `5m|15m|30m|1h|4h|1d` timeframes where backend data is available, pan/zoom, crosshair, OHLC display, responsive resizing, touch interaction, signal markers, and entry/SL/TP overlays. Keep calculations server-side; indicators in V1 are display overlays/settings only.

- [ ] **Step 4: Add no-data and API-error states**

Render a stable chart frame with a clear unavailable-data message when candles are empty or the request fails; never retain a previous symbol's chart while labeling it as the new symbol.

- [ ] **Step 5: Verify tests/build**

Run: `cd web && npm test -- --run tests/chart-overlays.test.ts tests/market-workspace.test.tsx && npm run build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/features/chart web/features/markets web/tests/chart-overlays.test.ts web/tests/market-workspace.test.tsx web/package.json
git commit -m "feat(web): add ATLAS trading chart workspace"
```

### Task 6: Add trades, signals, activity, and ATLAS AI assistant surfaces

**Files:**
- Create: `web/features/trades/positions-panel.tsx`
- Create: `web/features/signals/signals-panel.tsx`
- Create: `web/features/ai/atlas-assistant.tsx`
- Create: `web/features/ai/atlas-robot-mark.tsx`
- Create: `web/tests/positions-panel.test.tsx`
- Create: `web/tests/atlas-assistant.test.tsx`
- Modify: `web/features/dashboard/dashboard-screen.tsx`

**Interfaces:**
- Consumes: positions, signal/activity data, `sendAgentMessage()` from Task 3.
- Produces: `PositionsPanel`, `SignalsPanel`, `AtlasAssistant`, contextual assistant prompt submission with states `idle|sending|success|error`.

- [ ] **Step 1: Write failing positions and assistant tests**

Positions test must cover open-position rows, empty state, and unavailable backend state. Assistant test must cover prompt submit, sending state, success response, HTTP failure, and preservation of the user's prompt on failure.

- [ ] **Step 2: Run tests**

Run: `cd web && npm test -- --run tests/positions-panel.test.tsx tests/atlas-assistant.test.tsx`

Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement positions/signals/activity surfaces**

Show entry, current price, size, P/L, SL, TP, direction, execution status, signal confidence/rationale/risk warning/timestamp where backend provides those fields. Do not invent confidence or execution results.

- [ ] **Step 4: Implement the ATLAS AI assistant**

Use the existing agent chat endpoint through `sendAgentMessage()`. Present the robot as a visual brand mark plus concise contextual assistant UI; the robot must not imply a separate execution engine or claim a trade was executed based on chat success.

- [ ] **Step 5: Verify tests and build**

Run: `cd web && npm test -- --run tests/positions-panel.test.tsx tests/atlas-assistant.test.tsx && npm run build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/features/trades web/features/signals web/features/ai web/features/dashboard web/tests/positions-panel.test.tsx web/tests/atlas-assistant.test.tsx
git commit -m "feat(web): add ATLAS trades signals and AI assistant"
```

### Task 7: Wire live read-only dashboard data and preserve backend execution boundaries

**Files:**
- Create: `web/app/dashboard/page.tsx`
- Create: `web/lib/api/config.ts`
- Create: `web/components/system/backend-status.tsx`
- Create: `web/tests/backend-status.test.tsx`
- Modify: `web/app/page.tsx`
- Modify only if required for read-only aggregation: `app/dashboard/api.py`
- Modify only if required for CORS/deployment origin configuration: `app/main.py`
- Test if backend changed: existing relevant `tests/` files or a focused new backend API test.

**Interfaces:**
- Consumes: all frontend adapters/components from Tasks 2-6; existing FastAPI routes.
- Produces: production data flow from FastAPI into the dashboard, one environment-based API base URL, and a visible backend connectivity indicator.

- [ ] **Step 1: Write failing connectivity-state test**

Assert `BackendStatus` distinguishes `checking`, `online`, `offline`, and `degraded` and never labels a failed health/account call as connected.

- [ ] **Step 2: Run the test**

Run: `cd web && npm test -- --run tests/backend-status.test.tsx`

Expected: FAIL because connectivity component/config is missing.

- [ ] **Step 3: Implement environment-based API configuration**

Expose only a non-secret public backend origin, e.g. `NEXT_PUBLIC_ATLAS_API_BASE_URL`; never expose broker passwords, execution authorization, OpenAI keys, or server-only settings.

- [ ] **Step 4: Wire dashboard reads to existing backend routes**

Fetch health, cockpit/dashboard state, market briefing/quotes/candles, positions, and agent chat through the typed adapter. Add only the smallest FastAPI read adapter if an existing endpoint cannot supply a required V1 field; do not duplicate risk or execution logic in Next.js.

- [ ] **Step 5: If backend files changed, add a focused failing backend test first and make it pass**

Run the specific test with `python -m pytest -q <test-path>`; expected PASS after the minimal adapter/CORS change.

- [ ] **Step 6: Verify frontend and backend regression suites**

Run: `cd web && npm test -- --run && npm run build && npm run lint`

Run from repository root: `python -m pytest -q`

Expected: frontend PASS/build PASS/lint PASS and existing backend suite PASS.

- [ ] **Step 7: Commit**

```bash
git add web app tests
git commit -m "feat(web): connect ATLAS frontend to backend"
```

### Task 8: Production migration readiness and deployment verification

**Files:**
- Create: `web/.env.example`
- Create: `web/README.md`
- Create: `docs/deployment/atlas-webapp.md`
- Modify only when deployment target is confirmed: repository deployment config (`Dockerfile`, Cloudflare/Vercel config, or reverse-proxy config)
- Create: `web/tests/security-config.test.ts`

**Interfaces:**
- Consumes: complete frontend and backend integration from Task 7.
- Produces: documented build/start process, backend-origin configuration, migration path from legacy server-rendered root to new web app, rollback path, and secret-exposure guard.

- [ ] **Step 1: Write failing security-config test**

Assert committed frontend environment examples contain only public configuration names and that known secret variable names (`OPENAI_API_KEY`, `MT5_PASSWORD`, private authorization tokens) are absent from browser-facing config.

- [ ] **Step 2: Run security test**

Run: `cd web && npm test -- --run tests/security-config.test.ts`

Expected: FAIL until example/config contract exists.

- [ ] **Step 3: Document and implement the deployment contract**

Document local development, production build, API origin, health checks, how `justai-atlas.online` routes the web frontend and FastAPI API, and a rollback that restores the existing server-rendered dashboard without changing trading/risk state.

- [ ] **Step 4: Run full verification**

Run: `cd web && npm test -- --run && npm run build && npm run lint`

Run from repository root: `python -m pytest -q`

Expected: all PASS.

- [ ] **Step 5: Inspect built browser assets for secret names**

Run from `web/`: `grep -R "OPENAI_API_KEY\|MT5_PASSWORD\|ATLAS_LIVE_AUTH" .next/static || true`

Expected: no matches containing secret values or private authorization configuration.

- [ ] **Step 6: Commit**

```bash
git add web/.env.example web/README.md docs/deployment web/tests/security-config.test.ts Dockerfile
# include deployment files only if actually changed
git commit -m "docs(web): prepare ATLAS frontend deployment"
```

## Final Verification Gate

Before merging or pointing `justai-atlas.online` to the new frontend:

- [ ] `cd web && npm test -- --run` passes.
- [ ] `cd web && npm run build` passes.
- [ ] `cd web && npm run lint` passes.
- [ ] `python -m pytest -q` passes from repository root.
- [ ] Dashboard renders explicit offline state with backend stopped.
- [ ] Dashboard renders live account/risk data when backend is available.
- [ ] Chart changes symbol/timeframe without stale labels/data.
- [ ] ATLAS AI chat failure is shown as failure, never as execution success.
- [ ] Mobile layout has no horizontal overflow and bottom navigation remains reachable.
- [ ] Browser bundle inspection reveals no broker/OpenAI/private execution secrets.
- [ ] Production routing switch and rollback steps are documented before DNS/proxy changes.
