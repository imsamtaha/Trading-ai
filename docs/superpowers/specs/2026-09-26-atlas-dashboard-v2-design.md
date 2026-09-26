# ATLAS Dashboard V2 Design

## Goal
Make ATLAS a concise, mobile-first trading intelligence workspace centered on an editable chart where each authenticated trader can see their own setups and ATLAS signals.

## Experience
- Warm off-white base, ATLAS orange accents, graphite text; minimal dark surfaces.
- Reduce prose: prioritize numbers, state, charts, compact AI insights, and drill-down panels.
- Main sectors: Overview, AI Chart, Markets, Trade Center, Risk Center, Intelligence, Alerts, MT5/Broker, Performance, Subscription, Payments, Profile/Settings.
- Mobile navigation exposes the core sectors and a compact More menu.

## AI Chart
- Interactive symbol/timeframe chart with indicator controls and drawing/editing affordances.
- Overlay layers: My Setups, ATLAS Signals, Positions, Indicators.
- Setup/signal detail includes entry, stop, targets, state, timestamp, risk/context and confidence where available.
- Persist each trader's chart preferences/layout separately; never leak another trader's state.

## ATLAS AI
- Add an Ask ATLAS AI panel for product questions, chart explanation, market information and risk terminology.
- Chart context can be attached to questions, but the assistant is informational/analytical and does not silently execute account changes.
- Keep answers short by default and show provenance/timestamps for market-derived context when available.

## Commercial/Auth
- Plans: Starter $99/month, Pro $149/month, Elite $299/month. No free demo and no $49 tier in customer-facing pricing.
- Keep Whish as a payment path and make plan IDs/prices consistent across subscription and billing modules.
- Production Google OAuth must return users to https://justai-atlas.online rather than localhost; local callback remains development-only.

## Safety and quality
- Preserve account isolation, risk telemetry, auditability and existing execution controls while redesigning the UI.
- Do not claim guaranteed returns or fabricate signals/market data.
- Responsive behavior and degraded/offline states must remain usable.
- Existing tests stay green; new behavior receives focused tests before implementation.
