# ATLAS Dashboard V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a concise off-white/orange ATLAS workspace with interactive trader charts, setup/signal overlays, ATLAS AI, corrected pricing, Whish consistency, and production-safe Google OAuth.

**Architecture:** Extend the existing FastAPI dashboard rather than replace the trading core. Add focused dashboard endpoints/state for chart data and preferences, a bounded AI endpoint using server-side credentials, and keep UI rendering in the existing dashboard surface while preserving MT5/risk boundaries.

**Tech Stack:** Python 3.13, FastAPI, existing ATLAS intelligence/MT5 modules, pytest, browser JavaScript/CSS, existing Supabase integration where configured.

**Spec:** `docs/superpowers/specs/2026-09-26-atlas-dashboard-v2-design.md`

## Global Constraints
- Customer plans are Starter $99/month, Pro $149/month, Elite $299/month; no free demo/$49 customer tier.
- Production origin is `https://justai-atlas.online`; localhost is development-only.
- Preserve trader isolation, risk controls, auditability and current execution boundaries.
- Never expose API keys or broker credentials to browser code or logs.

## Review Focus
- Missing/stale market data must render an explicit unavailable state, never invented candles/signals.
- Trader chart preferences and setup overlays must not cross account boundaries.
- Unknown symbols/timeframes/indicators must be rejected or normalized safely.
- AI failures/timeouts must degrade without breaking dashboard or execution services.
- OAuth/payment configuration failures must show actionable status without exposing secrets.

---

### Task 1: Pricing and payment consistency
**Files:** Modify `app/billing/plans.py`, `app/billing/whish.py`, `app/subscription.py`; test `tests/test_payment_preferences.py`.
**Interfaces:** Produces canonical Starter/Pro/Elite plan IDs and prices consumed by subscription and Whish routes.
- [ ] Write failing tests asserting exactly Starter=99, Pro=149, Elite=299 and absence of free/$49 customer pricing.
- [ ] Run focused payment tests and confirm RED.
- [ ] Implement the minimal canonical plan/pricing changes and align Whish/subscription rendering.
- [ ] Run focused tests and confirm GREEN.

### Task 2: Dashboard shell and visual system
**Files:** Modify `app/dashboard/views.py`; create/modify focused dashboard tests.
**Interfaces:** Consumes existing `/dashboard/atlas` and market briefing state; produces Overview/AI Chart/Markets/Trade/Risk/Intelligence/Alerts/MT5/Performance/Subscription/Payments/Settings navigation.
- [ ] Write failing HTML contract tests for sectors, concise copy, mobile navigation, off-white/orange tokens and Ask ATLAS AI control.
- [ ] Confirm RED, implement minimal shell/CSS, then confirm GREEN.

### Task 3: Interactive chart state and overlays
**Files:** Modify `app/dashboard/api.py`, `app/dashboard/__init__.py`, `app/dashboard/views.py`; add `tests/test_dashboard_chart.py`.
**Interfaces:** Produces validated chart payload and per-trader layout/preferences; consumes existing ATLAS signal/position data.
- [ ] Write failing tests for symbol/timeframe validation, setup/signal/position layers, indicator allowlist and account isolation.
- [ ] Confirm RED; implement endpoints/state without fabricating missing candles; confirm GREEN.
- [ ] Add browser chart controls for timeframe, indicators, layer visibility and editable layout; verify mobile behavior.

### Task 4: ATLAS AI assistant
**Files:** Create `app/dashboard/assistant.py`; modify dashboard router/view; add `tests/test_dashboard_assistant.py`.
**Interfaces:** Produces `POST /dashboard/ai`; consumes sanitized user question plus optional current chart context, server-side AI credentials only.
- [ ] Write failing tests for empty input, chart context, bounded response shape, timeout/error degradation and no secret leakage.
- [ ] Confirm RED; implement the minimal assistant service/route; confirm GREEN.
- [ ] Wire compact Ask ATLAS AI panel to the endpoint and keep execution actions outside chat.

### Task 5: Production OAuth configuration
**Files:** Modify only repo-owned auth/config/docs discovered during implementation; add config contract tests where code-owned.
**Interfaces:** Production redirect resolves to `https://justai-atlas.online`; localhost remains development-only.
- [ ] Trace the current Google/Supabase redirect source and reproduce the localhost failure before changing it.
- [ ] Add a failing config test when the redirect is code-owned; otherwise record the exact provider/Supabase setting required.
- [ ] Apply the smallest production redirect fix without exposing client secrets; verify callback behavior.

### Task 6: Full verification and deploy readiness
**Files:** Tests/docs only as required by failures.
**Interfaces:** Consumes Tasks 1-5; produces a verified release candidate.
- [ ] Run all pytest tests and require zero failures.
- [ ] Smoke-test `/health`, `/dashboard`, chart endpoints, AI endpoint, `/subscribe`, Whish routes and OAuth entry/callback.
- [ ] Review `git diff` for secrets, unrelated changes and stale $49/free-demo copy.
- [ ] Deploy only through the repository's existing deployment path, then verify `https://justai-atlas.online` responses.
