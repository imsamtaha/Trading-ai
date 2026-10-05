# ATLAS Web App Option A — Design Spec

Date: 2026-09-27
Branch: `feat/atlas-webapp-option-a`

## Goal

Build the official ATLAS responsive web application inside the existing `imsamtaha/Trading-ai` repository, using the current FastAPI/MT5/risk/agent system as the backend and adding a dedicated modern frontend layer rather than creating a separate product repository.

## Product Intent

ATLAS should feel like a premium trading intelligence cockpit inspired by the approved mobile references: graphite-black surfaces, off-white metallic typography, orange energy accents, compact high-information cards, editable charts, visible risk controls, and a distinct ATLAS AI assistant presence.

The frontend must be useful on desktop, tablet, and mobile. Mobile should closely preserve the approved phone layout, while desktop should expand into a professional trading workspace with sidebar navigation and larger chart/data regions.

## Architectural Direction

The existing Python backend remains the source of truth for trading, account state, risk, agents, and MT5 integration.

Add a new frontend application under:

```text
web/
```

Recommended stack:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui primitives
- TradingView Lightweight Charts for candlesticks and overlays
- Recharts only where a simple statistics chart is more appropriate

The frontend communicates with the existing FastAPI backend through typed API client modules. Trading logic does not move into the browser.

Target structure:

```text
Trading-ai/
├── app/                  # existing FastAPI/backend domain
├── tests/                # existing backend tests
├── web/                  # new ATLAS web frontend
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── public/
│   └── tests/
├── docs/
└── ...
```

## V1 Scope

### 1. Dashboard

Show at a glance:

- ATLAS brand header
- MT5/FxPro connection state
- account mode/status
- balance
- equity
- floating P/L
- daily P/L
- margin or available funds where provided by backend
- risk level
- major market watch tiles

### 2. Main Trading Chart

Interactive candlestick chart with:

- symbol switching
- timeframes
- zoom/pan
- crosshair
- OHLC display
- signal markers
- entry / stop-loss / take-profit levels
- basic indicator overlays where supported
- mobile touch interaction

The frontend should expose editable chart settings without implementing trading calculations client-side.

### 3. Markets

Market watch area for instruments such as:

- EURUSD
- GBPUSD
- XAUUSD
- BTC/USDT where supported
- additional backend-supported instruments

Each tile should support price, percentage move, compact sparkline, and status.

### 4. Trades

Display:

- open positions
- pending positions/orders where relevant
- closed/history
- entry price
- current price
- size
- P/L
- stop loss
- take profit
- execution status

Any execution action must call existing backend execution/risk endpoints and must never bypass the backend risk layer.

### 5. Risk Control Center

Prominent risk panel matching the approved design language:

- overall risk
- daily loss usage
- account drawdown
- exposure
- position-size utilization
- aggregate open risk
- risk warnings
- current protection state

Changing a risk setting should use backend APIs and should not silently modify execution behavior in the browser.

### 6. ATLAS AI Assistant

Persistent AI assistant surface inspired by the approved robot reference.

Capabilities in V1 UI:

- market explanation
- signal explanation
- risk explanation
- portfolio review
- recent activity explanation
- contextual prompts based on the current instrument/account screen

The assistant uses existing ATLAS agent/backend endpoints. The robot is a visual/brand element, not a separate execution engine.

### 7. Signals and Activity

Show:

- current signals
- confidence where backend provides it
- direction
- timestamp
- rationale summary
- risk warnings
- recent agent/activity events

### 8. Navigation

Desktop:

- left sidebar

Mobile:

- bottom navigation

Primary destinations:

- Dashboard
- Markets
- Trade
- Signals
- Risk
- Analytics
- News
- ATLAS AI
- Account

## Visual System

### Palette

- background: near-black / graphite
- surfaces: dark graphite with subtle elevation
- primary accent: vivid ATLAS orange
- text: off-white / metallic white
- success: restrained green
- warning: amber/orange
- info/holographic AI accents: limited cool blue

### Style

- rounded rectangular cards
- thin low-contrast borders
- subtle inner highlights
- restrained glow rather than heavy neon everywhere
- compact financial typography
- large metallic ATLAS wordmark
- orange highlight for active navigation and CTAs
- depth through shadows and layered panels

The interface should feel premium and functional, not like a static concept render.

## Responsive Layout

### Desktop

```text
┌──────────────┬───────────────────────────────────────────────┐
│ Sidebar      │ Header / Account / Balance / Risk            │
│              ├───────────────────────────────────────────────┤
│ Dashboard    │                                               │
│ Markets      │              Main Trading Chart               │
│ Trade        │                                               │
│ Signals      ├──────────────────────────┬────────────────────┤
│ Risk         │ Open Positions / Signals │ ATLAS AI Assistant │
│ Analytics    ├──────────────────────────┴────────────────────┤
│ News         │ Risk / Activity / Analytics                  │
│ Account      │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

### Mobile

Preserve the approved stacked flow:

1. brand/header
2. account + balance
3. market tiles
4. main chart
5. primary action cards
6. risk controls
7. positions/activity
8. bottom navigation

## API Integration Strategy

Create a typed frontend adapter layer under `web/lib/api/`.

Initial integrations should reuse existing backend endpoints wherever available, including current ATLAS dashboard, market briefing, MT5 cockpit/account state, agent chat/tools, trading/risk status, and related data.

Where an exact endpoint is missing, add the smallest backend API adapter needed rather than duplicating domain logic in Next.js.

## Safety and Execution Boundaries

- UI does not calculate or override backend risk authorization.
- UI does not store broker credentials in client-side code.
- secrets remain server-side.
- execution requests remain auditable.
- any user-visible trade action must clearly show current account/mode and result status.
- frontend errors must never be interpreted as successful execution.

## Implementation Sequence

1. scaffold `web/`
2. create theme/tokens/layout shell
3. build responsive navigation
4. build dashboard cards using mock typed fixtures
5. build interactive market chart
6. build risk panel
7. build trades/activity panels
8. build ATLAS AI assistant panel
9. add typed API client
10. connect dashboard/account/risk/agents endpoints
11. add loading/error/offline states
12. test responsive behavior
13. run frontend build/lint/tests
14. run existing backend tests to confirm no regression
15. prepare deployment integration for `justai-atlas.online`

## Testing Requirements

Frontend:

- component tests for core cards and state mapping
- API adapter tests
- navigation/responsive smoke tests
- build and lint must pass

Backend regression:

- existing Python test suite must remain passing

Integration smoke tests:

- backend health reachable
- dashboard account data renders
- chart loads with valid series data
- AI assistant request returns/rendered state
- risk data maps correctly
- no client-side secret exposure

## Non-Goals for V1

Do not add unrelated product expansion while building the new shell. Specifically defer:

- strategy marketplace
- social trading
- custom scripting editor
- full broker onboarding marketplace
- advanced billing redesign
- portfolio tax reporting
- mobile native application

## Success Criteria

V1 is successful when:

- ATLAS has one official responsive frontend inside `Trading-ai`
- the UI visually matches the approved ATLAS dark/orange premium identity
- mobile resembles the approved phone concept closely
- desktop provides a proper trading workspace rather than a stretched mobile page
- current MT5/account/risk/agent data can be rendered from the existing backend
- chart interaction works smoothly
- no backend trading/risk behavior is bypassed
- frontend tests/build and existing backend tests pass
- the app is ready to attach to the production domain after deployment configuration
