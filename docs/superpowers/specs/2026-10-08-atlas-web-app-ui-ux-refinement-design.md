# ATLAS Web App UI/UX Refinement Design

Date: 2026-10-08  
Status: Approved design, pending implementation plan  
Scope: `runtime/web-ui` and shared presentation components only

## 1. Intent

Refine the existing ATLAS web application into one coherent product experience across public preview, login, connect, dashboard, ATLAS AI, news, and mobile navigation.

The approved concept image is the visual north star, not a requirement for pixel-for-pixel duplication. The shipped UI must preserve working authentication, APIs, Paper runtime behavior, and current security boundaries while moving the product toward the same premium dark/orange desktop-and-mobile experience.

Success means a user can move from landing or preview to login, then into the dashboard and connected views without feeling that each screen belongs to a different application.

## 2. Product Constraints

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

## 3. Visual Direction

ATLAS should use a restrained premium trading-intelligence aesthetic:

- Dark navy and near-black surfaces.
- Metallic orange as the primary accent.
- Cool blue/cyan only for secondary data accents.
- Restrained glow, not neon saturation everywhere.
- Strong hierarchy through spacing, typography, borders, and surface depth.
- Cards use consistent radii, border opacity, padding, and shadow depth.
- Status chips are concise and visually distinct.
- Dense trading data remains readable on mobile.
- Decorative 3D effects never reduce legibility.

The concept image establishes the target feel:
- recognizable ATLAS brand at first glance,
- chart-first dashboard composition,
- ATLAS AI as a first-class feature,
- clearly separated market data, positions, news, and system state,
- matching desktop and mobile visual language.

## 4. Shared Application Shell

The application shell becomes the source of truth for:

- brand presentation,
- top-level spacing,
- language control,
- Paper Mode state,
- backend/system health state,
- navigation treatment,
- page width and responsive gutters,
- loading and error presentation.

The shell should feel stable while page content changes.

### Desktop

Desktop uses a compact top utility/navigation area with:
- ATLAS brand,
- primary navigation,
- language switch,
- Paper Mode,
- system/session state,
- user/account entry point when signed in.

The dashboard itself remains content-dense but gets clearer separation between primary decision surfaces and secondary monitoring panels.

### Mobile

Mobile uses:
- compact brand header,
- sticky five-item bottom navigation,
- large touch targets,
- safe-area bottom spacing,
- no horizontal overflow,
- stacked cards with predictable vertical rhythm.

Primary mobile navigation:
1. Markets
2. Signals
3. Risk
4. News
5. ATLAS AI

## 5. Landing / Public Preview

The public root route continues to render the ATLAS application preview but should read as a deliberate public product entry point.

Changes:
- stronger hero/brand hierarchy,
- clear Paper-only messaging,
- obvious paths to Sign in, Dashboard Preview, and Connect,
- public market/news content may be visible,
- private account values remain private,
- authenticated-only controls render as locked or sign-in actions rather than disappearing unpredictably.

The preview must not imply broker execution availability.

## 6. Login

The login page keeps the current two-column desktop concept and becomes visually consistent with the rest of the product.

Required behavior:
- Google sign-in remains the primary action.
- Email magic-link remains secondary.
- Google button must initiate OAuth without waiting on the external Supabase browser bundle.
- Loading, success, error, and callback states are visibly distinct.
- Mobile collapses to one column without losing brand context.
- Paper-only and privacy messaging stays concise.

## 7. Connect

The current Connect page should stop looking like a utility form and become a guided account/data connection experience.

Structure:
1. Page header and current connection state.
2. Sign-in gate when required.
3. MT5 data connection card.
4. Council/runtime status for authorized users.
5. Clear Paper-only safety note.
6. Links to Dashboard and Subscription.

No UI may present live broker execution as enabled.

## 8. Dashboard Information Hierarchy

The dashboard is organized into four levels.

### Level 1: Orientation

Top bar:
- ATLAS brand,
- Paper Mode,
- user role/private state,
- MT5 data connection state.

Command strip:
- Simulation,
- Risk,
- Council.

### Level 2: Decision Surface

The most visually prominent section:
- market selector,
- timeframe,
- chart,
- signal context,
- position levels when available.

Insight cards:
- Trend,
- Signal,
- Bias,
- Confidence.

Account/stat strip:
- Balance,
- Equity,
- P/L,
- Positions,
- Engine.

Private data that is unavailable remains clearly labeled instead of being replaced with misleading values.

### Level 3: ATLAS AI

ATLAS AI is a primary feature card, not a footer utility.

States:
- ready,
- sending,
- response,
- error,
- locked/sign-in required,
- subscription required.

Suggested quick actions may include:
- analyze selected market,
- explain risk state,
- summarize market news.

The assistant remains informational and Paper-workspace scoped.

### Level 4: Monitoring

Secondary surfaces:
- markets,
- open positions,
- signals,
- risk,
- activity,
- performance,
- three market news items,
- Paper execution-agent status.

These use a shared card grammar so the lower dashboard feels like one system.

## 9. News

Display no more than three primary headlines in the dashboard.

Each item includes:
- headline,
- source,
- optional relative time when available,
- link to source.

Arabic mode prefers Arabic presentation when the feed supplies Arabic content. English mode uses English source content.

News must visually separate source metadata from headline text and support long titles without breaking layout.

## 10. ATLAS AI

ATLAS AI uses:
- ATLAS logo,
- clear online/locked state,
- one input,
- one primary send action,
- concise status feedback.

Locked states remain visible rather than removing the feature.

Authentication and entitlement rules remain unchanged.

## 11. Loading, Empty, Error, and Locked States

Create a consistent state language across the app.

### Loading
- lightweight skeleton or reserved layout,
- no large layout shifts,
- clear status text for long-running data fetches.

### Empty
- concise explanation,
- next action when useful.

### Error
- what failed,
- whether retry is possible,
- never expose internal stack traces.

### Locked
- explain why access is unavailable,
- link to Sign in or Subscription as appropriate.

These states should replace scattered plain-text placeholders where practical.

## 12. RTL / LTR

Arabic and English share the same component structure.

Rules:
- `dir` changes at workspace/page level.
- icon meaning does not reverse unless directional.
- numeric market data remains easy to scan.
- alignment changes must not reorder critical status meaning.
- language switching must not cause large layout jumps.

## 13. Accessibility

Minimum requirements:
- visible keyboard focus,
- semantic heading order,
- useful button/link names,
- minimum practical touch target sizing,
- adequate contrast,
- reduced-motion behavior for nonessential animation,
- no color-only communication for status.

## 14. Component Boundaries

Prefer targeted improvements to existing components.

Primary files/components expected to change:
- `app/atlas-app-shell.tsx`
- `app/login/page.tsx`
- `app/connect/page.tsx`
- `features/dashboard/dashboard-screen.tsx`
- `features/ai/atlas-assistant.tsx`
- `components/layout/atlas-shell.tsx`
- `components/layout/mobile-nav.tsx`
- `app/globals.css`

Small shared presentation components may be extracted when they remove duplication, such as:
- status pill,
- section header,
- empty/error state,
- page header.

Do not refactor unrelated backend or runtime code.

## 15. Data Flow

No new trading-data architecture is required.

Existing flow remains:

Backend/public APIs -> frontend fetch helpers -> app shell state -> dashboard components.

Authentication remains:

ATLAS Login -> Supabase Auth -> Google or email -> ATLAS callback -> backend private session -> dashboard.

News remains sourced through the public market-briefing endpoint.

## 16. Safety Boundary

The UI must continue to communicate and enforce:

- `PAPER MODE`,
- broker execution disabled,
- MT5 may be used as a market-data/data-connection source,
- Paper positions and Paper training are simulations,
- no live execution control is introduced by this redesign.

## 17. Verification

Implementation is not complete until all of the following pass:

1. Relevant React/Vitest UI tests.
2. Auth/login tests.
3. Dashboard/mobile tests.
4. Next.js production build.
5. Local HTTP smoke tests for root, login, connect, dashboard, backend health.
6. Public-domain HTTP smoke tests.
7. Google OAuth initiation reaches `accounts.google.com` without `invalid_client`.
8. Desktop visual review at common laptop width.
9. Mobile visual review at common phone width.
10. Arabic RTL and English LTR review.
11. Paper Monitor, Backend, and Frontend scheduled tasks remain healthy after deployment.

## 18. Rollout

Use the existing safe production build workflow:

1. Build into a temporary Next build directory.
2. Run tests and production build validation.
3. Keep the current `.next-production` as rollback.
4. Swap the validated build into `.next-production`.
5. Restart only the frontend task unless backend changes are truly required.
6. Run local and public smoke tests.
7. Retain a timestamped rollback build.

## 19. Non-Goals

This design does not:
- enable real-money trading,
- add broker order submission,
- replace Supabase authentication,
- redesign the backend architecture,
- add a new billing system,
- create a separate native mobile app,
- duplicate the dashboard into a second frontend.

## 20. Acceptance Criteria

The refinement is accepted when:

- the live web app visually matches the approved ATLAS concept direction,
- landing/login/connect/dashboard feel like one product,
- Google sign-in still works,
- mobile and desktop share the same visual language,
- ATLAS AI and News are clearly integrated,
- Arabic and English layouts are coherent,
- loading/empty/error/locked states are consistent,
- production build and smoke tests pass,
- Paper-only safety remains intact.
