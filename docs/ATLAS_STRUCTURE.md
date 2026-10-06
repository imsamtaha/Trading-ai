# ATLAS Final Structure

This document defines the canonical ATLAS repository and runtime architecture.

## 1. Decision architecture

The supported intelligence path is:

Market Data
-> Deterministic specialist analysis
-> Council adapters
-> ATLAS Council
-> Senior Risk Management
-> Executive Agent
-> PAPER TradeIntent
-> Paper outcome
-> Training journal
-> Reliability calibration profile
-> Future Council weighting

The intelligence and learning layers must remain broker-neutral.

## 2. Canonical modules

### Market and analysis
- app/data/
- app/analysis/
- app/strategies/

These modules produce normalized market facts, technical state, structure, signals, and trade candidates.

### Council and intelligence
- app/intelligence/council.py
- app/intelligence/council_adapters.py
- app/intelligence/executive.py
- app/intelligence/council_training.py
- app/intelligence/journal.py
- app/intelligence/confidence.py
- app/intelligence/regime/

Responsibilities:
- normalize specialist opinions
- reject stale or malformed inputs
- apply calibrated agent weighting
- require explicit Senior Risk approval
- produce a Paper-only final TradeIntent
- record settled Paper evidence
- update reliability weights only after sufficient samples

### Senior Risk
- app/risk/

Risk remains deterministic and authoritative. Council confidence cannot override a risk rejection.

### Paper execution
- app/paper_trading/
- app/database/

Paper execution simulates positions and outcomes locally. It is the only execution environment used by Council training.

### Broker isolation
- app/execution/

Broker adapters are isolated infrastructure. Council, Executive, and training modules must not import broker-send functions or call order_send.

### Dashboard and public surfaces
- app/dashboard/
- app/website.py
- web/
- frontend/

Public and subscriber-facing surfaces must not expose private broker-write capabilities.

### Agent APIs
- app/agent/

These provide assistant-facing analysis and safe tools. Paper-write tools remain explicitly gated.

## 3. Runtime state

Runtime-only state belongs outside Git:
- data/
- local SQLite databases
- journals
- logs
- generated profiles
- caches
- environment files
- build output

Persistent Windows state may be stored under the ATLAS server state directory, but it must remain outside source control.

Current Council-training state files:
- atlas_council_training.jsonl
- atlas_council_profile.json

## 4. Training policy

Training input must satisfy all of the following:
- source environment is PAPER
- broker_execution_allowed is false
- snapshot IDs match
- agent confidence values are finite and bounded
- settled outcome is known
- Council opinion metadata is present

Historical trades that predate Council metadata are not valid training examples.

Minimum sample threshold per agent: 5 settled Paper examples.

Before the threshold, weight remains 1.0.

Learned weights are bounded between 0.5 and 1.5.

## 5. Fail-closed rules

Executive decision becomes HOLD when:
- Council has no opinions
- Senior Risk is absent or not RISK_ACCEPTABLE
- any required score is malformed or non-finite
- data quality is below threshold
- Council conflict is too high
- directional weights tie
- stale snapshot evidence is detected upstream

These rules are safety invariants, not tuning suggestions.

## 6. Compatibility modules

Some files still contain demo naming because existing tests or runtime workflows reference them.

Examples:
- app/dashboard/demo_panel.py
- app/monitor/demo_session.py
- scripts/start_atlas_demo.ps1
- scripts/start_demo_session.ps1
- docs/DEMO_OPERATIONS.md
- web/assets/demo-model.js

They remain for compatibility. They are not the preferred architecture for new development.

Do not delete a compatibility file until its references and regression tests are migrated.

## 7. Files removed during final cleanup

The following files were removed because they were confirmed redundant or unreferenced:
- app/data/market.py.backup
- START_DEMO.ps1
- docs/FRIEND_DEMO_ACCESS.md

The active market provider remains app/data/market.py.

The documented runtime launcher remains under scripts/.

## 8. Repository hygiene rules

Ignored artifacts include:
- Python caches
- pytest caches
- virtual environments
- node_modules
- secrets and environment files
- databases
- runtime data
- logs
- generated builds
- backup and temporary files

Backup extensions such as .backup, .bak, .tmp, and .temp must not be committed.

Supabase migrations are immutable history and are not cleanup targets.

## 9. Validation gates

Before merging structural changes:
1. Run focused Council/Executive/training tests.
2. Run the full Python suite.
3. Run Node/browser tests where applicable.
4. Verify public health.
5. Verify broker execution remains disabled.
6. Verify Paper training remains broker-neutral.
7. Confirm repository status is clean.

## 10. Canonical product boundary

ATLAS is market intelligence, risk control, Paper simulation, monitoring, and decision support.

The current Council architecture is Paper-first.

Any future demo-broker or live-broker execution must remain a separately authorized execution layer and must never be enabled implicitly by Council training, UI state, or learned confidence.
