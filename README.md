# ATLAS Trading Intelligence

ATLAS is an AI-assisted market-intelligence and risk-control platform with a strict Paper-first boundary.

## ATLAS INTELLIGENCE · Tiger Shield Command Center

[Open the private ATLAS INTELLIGENCE dashboard](https://atlas-intelligence.imsamtaha-ai.chatgpt.site/) with an authorized account.

[Market data](https://atlas-intelligence.imsamtaha-ai.chatgpt.site/#market) · [Training](https://atlas-intelligence.imsamtaha-ai.chatgpt.site/#training) · [Saved workspace](https://atlas-intelligence.imsamtaha-ai.chatgpt.site/#workspace) · [Tiger Shield Command Center](https://atlas-intelligence.imsamtaha-ai.chatgpt.site/#connections)

- **Market data** provides exchange quotes. The portfolio and paper fills are simulated.
- **Training** shows Council evidence and demo experiments. **Saved workspace** stores preferences, watchlists, and simulated fill history.
- **Connections** shows integration status. Open [Agent Lab · مختبر الوكلاء](https://atlas-agent-lab-sam.imsamtaha-ai.chatgpt.site/) from the dashboard sidebar or directly to use the four-agent paper trading simulator.

- **Bigdata.com** opens the [research workspace](https://app.bigdata.com/). The dashboard has no Bigdata.com feed.
- **Supabase** migrations belong to [Trading-ai](supabase/migrations). The hosted dashboard uses its Sites database for Saved workspace.

![ATLAS Tiger Shield](docs/assets/atlas-tiger-shield.webp)

## Canonical architecture

Market Data -> Specialist Analysis -> ATLAS Council -> Senior Risk Management -> Executive Agent -> PAPER TradeIntent -> Paper Journal -> Council Calibration

The Council and Executive layers do not own a broker adapter and do not send MT5 orders.

## Current safe runtime

Default safety flags:
- ATLAS_LIVE_TRADING=false
- ATLAS_DASHBOARD_ONLY=true
- ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false

Core rules:
- Senior Risk must explicitly return RISK_ACCEPTABLE before an actionable Paper intent can be produced.
- Missing, malformed, stale, non-finite, low-quality, or highly conflicting input fails closed to HOLD.
- Executive output is always PAPER and broker_execution_allowed is false.
- Council training accepts only settled Paper outcomes.
- Old trades without Council opinion metadata are not used for learning.
- Agent weights remain at baseline until the minimum sample threshold is reached.

See docs/ATLAS_STRUCTURE.md for the final repository and runtime structure.

## Repository layout

app/analysis
Deterministic technical and structure analysis.

app/agent
Assistant APIs and safe tools.

app/billing
Subscription and payment surfaces.

app/dashboard
Compatibility routes for market, account and training data.

app/data
Market-data providers and normalization.

app/database
Local Paper account and trade persistence.

app/execution
Isolated broker adapters. This layer must not be imported into Council training.

app/intelligence
Council, Executive, scoring, regime, adapters, journal, and training.

app/monitor
Compatibility and runtime monitoring.

app/paper_trading
Simulated Paper position engine and ledgers.

app/risk
Deterministic Senior Risk controls.

app/strategies
Signal and trade-candidate logic.

scripts/
Validation, build, runtime, and Council-training utilities.

tests/
Python and Node regression and safety tests.

web/
Council reference material and assets used by the API and sign-in integration.

frontend/
Source for the browser authentication bundle.

docs/
Architecture, deployment, and operations documentation.

supabase/
Database migrations and policies. Migration history is preserved.

cloudflare/
Tunnel and deployment support.

atlas-skills/
ATLAS skill definitions.

Runtime data, caches, local databases, generated builds, logs, secrets, backup files, and temporary files are excluded from Git.

## Council training

The Paper-only learning path is implemented by:
- app/intelligence/council.py
- app/intelligence/executive.py
- app/intelligence/council_adapters.py
- app/intelligence/council_training.py
- scripts/train_atlas_council.py

Training is conservative. Each agent begins at weight 1.0 and does not receive a learned weight until enough settled Paper examples exist. Learned weights are bounded so a small sample cannot dominate the Council.

## Local API

Create the Python environment, install requirements, then start Uvicorn with live trading disabled and dashboard-only enabled.

Recommended local API port: 8012.

Health endpoint: GET /health

The public API must not expose private broker telemetry or broker-write permissions.

## Hosting

Trading-ai provides the backend, authentication, and Council research. The live ATLAS service has its own source and deployment.

## MT5

MT5 is a separate Windows-side integration boundary.

Read README_MT5.md and ATLAS_LAUNCH.md before changing the connector.

Council training, Paper simulation, and dashboard rendering must remain usable without broker-write access.

## Validation

Full Python suite:
python -m pytest -q

Focused Council suite:
python -m pytest -q tests/test_atlas_executive_paper_architecture.py tests/test_atlas_council_training.py tests/test_atlas_council_adapters.py

Browser/auth checks:
node --test tests/test_google_auth.mjs
node --test tests/test_demo_model.cjs

## Deployment references

- docs/GOOGLE_CLOUD_DEPLOY.md
- docs/GOOGLE_SIGN_IN.md
- docs/DEPLOY_EXECUTION_STATUS.md
- docs/DEMO_OPERATIONS.md

Some demo-named modules and scripts remain only because current compatibility tests and runtime workflows still reference them. They are not the canonical architecture. New work should target the Council -> Senior Risk -> Executive -> Paper flow.

## Repository hygiene

Do not commit secrets, .env files, local databases, runtime data, logs, caches, generated build output, or backup/temp artifacts.

Supabase migrations are historical database state and must not be deleted merely because files look similar.

## Product boundary

ATLAS provides market intelligence, risk controls, Paper simulation, monitoring, and decision-support context. It does not guarantee outcomes. Public and subscriber surfaces must not silently acquire broker execution permissions.
