# ATLAS Trading Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved premium bilingual Trading Hub inside the canonical ATLAS dashboard without weakening its read-only/manual-execution boundary.

**Architecture:** Keep `/atlas-ultimate` and the existing FastAPI dashboard APIs as the source of truth. Evolve the existing HTML/CSS/JS shell rather than introducing a second frontend, and make localization explicit for dynamic market/demo rendering. Keep paper-demo functionality isolated and visually secondary to the customer command center.

**Tech Stack:** Python, FastAPI, embedded HTML/CSS/JavaScript, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-atlas-trading-hub-design.md`

## Global Constraints
- Preserve `/atlas-ultimate` as the canonical customer route and `/dashboard` redirect behavior.
- Preserve read-only subscriber access and disabled public broker execution.
- Preserve existing API contracts unless a failing test proves a required compatibility change.
- Keep JUST AI, ATLAS, MT5, P/L, currencies and ticker symbols LTR where appropriate.
- Arabic descriptive UI must render coherently RTL.
- Start from the verified 236-test baseline and use TDD for new behavior.

---

### Task 1: Trading Hub shell and visual system

**Files:**
- Modify: `app/dashboard/views.py`
- Modify: `app/dashboard/__init__.py`
- Test: `tests/test_atlas_canonical_dashboard.py`

**Interfaces:**
- Consumes: existing `DASHBOARD_HTML`, `_atlas_ultimate_html()` and canonical routing.
- Produces: Trading Hub identity, section anchors and reusable 3D button/card styling.

- [ ] **Step 1: Write failing canonical UI tests**

Add assertions that `_atlas_ultimate_html()` contains `TRADING HUB`, section navigation targets for account/analytics/markets/demo, and a single canonical refresh control set.

- [ ] **Step 2: Run the canonical tests and verify RED**

Run: `python -m pytest tests/test_atlas_canonical_dashboard.py -q`
Expected: new Trading Hub assertions fail while existing tests remain green.

- [ ] **Step 3: Implement the Trading Hub shell**

Update the existing dashboard HTML/CSS to add the branded header/navigation, section IDs, responsive command-center layout, premium font stacks, metallic card depth and raised `.btn` states (`hover`, `active`, `focus-visible`). Do not create a new route.

- [ ] **Step 4: Remove redundant canonical refresh injection if the base dashboard already owns those controls**

Keep one `Refresh All` and one relevant module refresh control source of truth.

- [ ] **Step 5: Run canonical tests**

Run: `python -m pytest tests/test_atlas_canonical_dashboard.py -q`
Expected: PASS.

### Task 2: Arabic dynamic market localization

**Files:**
- Modify: `app/dashboard/preferences.py`
- Modify: `app/dashboard/views.py`
- Test: `tests/test_atlas_canonical_dashboard.py`

**Interfaces:**
- Consumes: stored `atlas-language` preference and `atlas-language-change` event.
- Produces: localization helper used by dynamic dashboard rendering.

- [ ] **Step 1: Add failing tests for dynamic Arabic terms**

Cover quote-time labels, freshness states, direction states, market categories, empty/error states and refresh labels.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_atlas_canonical_dashboard.py -q`
Expected: uncovered dynamic terms fail.

- [ ] **Step 3: Implement explicit dynamic localization**

Expose a small browser-side localization function from `preferences.py` and use it from `views.py` when constructing market rows and status strings. Keep symbols/tickers isolated with `bdi dir="ltr"`.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_atlas_canonical_dashboard.py -q`
Expected: PASS.

### Task 3: Demo Panel localization and visual integration

**Files:**
- Modify: `app/dashboard/demo_panel.py`
- Modify: `app/dashboard/preferences.py`
- Test: `tests/test_atlas_canonical_dashboard.py`
- Test: existing demo-panel tests discovered by pytest.

**Interfaces:**
- Consumes: `/dashboard/demo-status`, `/dashboard/trader-view`, localization preference/event.
- Produces: localized, visually secondary paper-demo module inside the Trading Hub.

- [ ] **Step 1: Add failing localization tests**

Assert coverage for `FORWARD DEMO VALIDATION`, `ATLAS Demo Trading`, `Open Paper Trades`, `Closed Trades`, `Review Target`, `Profit Factor`, `Expectancy`, `Drawdown / Risk`, `Latest Demo Events`, `Live Readiness Gate`, `Performance Center`, filters, readiness/empty states and paper-demo disclaimer.

- [ ] **Step 2: Verify RED**

Run the canonical and demo-related tests.
Expected: English-only demo copy fails localization coverage.

- [ ] **Step 3: Localize static and dynamic demo content**

Render descriptive strings through the shared localization helper, react once to `atlas-language-change`, and preserve `ATLAS`, `MT5`, `P/L`, asset symbols and timeframe tokens where technically appropriate.

- [ ] **Step 4: Integrate the demo module below primary intelligence sections**

Keep its safety wording explicit: local simulated/paper evidence, no broker orders, no real P/L, no automatic live activation.

- [ ] **Step 5: Verify demo tests GREEN**

Run relevant tests and confirm no duplicated language-refresh path.

### Task 4: Mobile/RTL hardening

**Files:**
- Modify: `app/dashboard/views.py`
- Modify: `app/dashboard/demo_panel.py`
- Modify: `app/dashboard/preferences.py`
- Test: `tests/test_atlas_canonical_dashboard.py`

**Interfaces:**
- Consumes: Trading Hub shell and localized modules.
- Produces: mobile-safe RTL/LTR presentation.

- [ ] **Step 1: Add structural regression assertions**

Assert presence of mobile breakpoints, RTL selectors, LTR symbol isolation, minimum button sizing and section anchors.

- [ ] **Step 2: Implement responsive refinements**

Use single-column mobile flow, touch-friendly controls, wrapping status/navigation elements, readable Arabic line-height and no fixed widths that force horizontal overflow.

- [ ] **Step 3: Run canonical tests**

Expected: PASS.

### Task 5: Full regression and runtime verification

**Files:**
- No production changes unless verification exposes a root-cause defect.

**Interfaces:**
- Consumes: completed Trading Hub implementation.
- Produces: auditable release evidence.

- [ ] **Step 1: Run full suite**

Run: `python -m pytest -q`
Expected: all previous 236 tests plus new Trading Hub tests pass, 0 failures.

- [ ] **Step 2: Verify canonical routing**

Run:
```bash
curl --max-time 10 -s -o /dev/null -w "/dashboard -> HTTP %{http_code} | redirect=%{redirect_url}\n" http://127.0.0.1:8001/dashboard
curl --max-time 20 -s -o /dev/null -w "/atlas-ultimate -> HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8001/atlas-ultimate
```
Expected: `/dashboard` redirects to `/atlas-ultimate`; canonical route returns HTTP 200.

- [ ] **Step 3: Visual verification**

Open `http://127.0.0.1:8001/atlas-ultimate`, inspect Arabic and English on mobile, verify the demo module is localized and secondary, and confirm no horizontal clipping or duplicate refresh controls.

- [ ] **Step 4: Record verification evidence**

Report exact pytest count, routing codes, runtime response and any remaining visual discrepancy. Do not claim MT5 execution stability from dashboard tests.
