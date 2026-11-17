# ATLAS Trading Hub Design

## Goal
Transform the existing `/atlas-ultimate` customer dashboard into a premium bilingual JUST AI / ATLAS TRADING HUB while preserving the current read-only/manual-execution safety boundary and existing backend APIs.

## Visual direction
Use the approved concept as the visual target: graphite-black layered surfaces, metallic silver borders, restrained orange edge lighting, strong depth, crisp vector/CSS rendering, raised 3D controls, premium Arabic typography, and a responsive mobile-first layout. “2K” means high-density/vector-quality UI treatment rather than bitmap-sized HTML controls.

## Information architecture
The canonical `/atlas-ultimate` route remains the single customer entry point. The page gains a branded Trading Hub shell with a prominent `JUST AI · ATLAS ULTIMATE · TRADING HUB` identity, compact navigation/section anchors, system status, account telemetry, ATLAS analytics, market intelligence/news, risk context, and a dedicated paper-demo validation area. The demo panel must no longer visually dominate the top of the customer experience.

## Localization
Arabic mode must be genuinely RTL and coherent. Descriptive copy, labels, states, buttons, demo analytics, filters, empty states, readiness messages and dynamic market UI must localize. Brand/technical tokens such as JUST AI, ATLAS, MT5, P/L, currency codes and ticker symbols remain LTR/English where appropriate. Dynamic JavaScript rendering must use localization-aware output rather than relying only on a post-render text walker.

## Safety and product boundary
The Trading Hub is market intelligence and monitoring software. Public subscriber broker execution remains disabled/read-only. Paper demo analytics must remain clearly labeled as simulated/local paper evidence and must not be presented as broker P/L or authorization for live trading.

## Responsive behavior
Desktop uses a dense command-center composition. Tablet collapses secondary columns. Mobile uses a single primary flow with readable Arabic text, full-width cards where needed, touch-friendly raised controls, and no horizontal clipping.

## Acceptance criteria
- Canonical route remains `/atlas-ultimate` and `/dashboard` redirects to it.
- Existing market/account APIs and read-only execution boundary are preserved.
- Arabic mode does not leave the demo panel or dynamic UI predominantly English.
- Trading Hub identity and section navigation are visible without creating a second dashboard route.
- Buttons have consistent raised 3D treatment, focus/pressed states and adequate touch targets.
- Existing regression suite remains green and new localization/Trading Hub tests are added.
