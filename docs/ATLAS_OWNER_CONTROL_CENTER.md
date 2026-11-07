# ATLAS Owner Control Center (/sam)

Private, read-only FastAPI dashboard. Arabic and RTL by default, English optional. This is a separate surface from trader /traders and the public / website.

## Security and isolation

- Page, JavaScript, CSS and /sam/api/snapshot require HTTP Basic credentials. Username defaults to sam; password must be at least 16 characters. Without it, owner routes return 503.
- Set ATLAS_OWNER_DASHBOARD_PASSWORD in the deployment secret store or Windows .env, never in Git or the browser. Optionally set ATLAS_OWNER_DASHBOARD_USERNAME.
- HTTPS is mandatory in production because Basic authentication credentials otherwise travel as cleartext. Redirect HTTP to HTTPS at the proxy/tunnel and bind the backend to loopback.
- Responses use no-store, noindex, frame blocking, restrictive CSP and an asset allowlist. The public static website build excludes owner UI files.
- No broker-write imports, endpoints, buttons or actions in the owner surface. Its only network action is GET /sam/api/snapshot.
- Keep ATLAS_DASHBOARD_ONLY=true, ATLAS_LIVE_TRADING=false and ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false.

## Trusted evidence export contract

Set ATLAS_OWNER_EVIDENCE_DIR to a private, operator-reviewed, nonpublic directory. Optional filenames:

- overview.json: verified PAPER KPIs and council summaries
- agents.json: agent votes, confidence, weights and conflict scores
- signals.json: signal confidence, source and risk
- risk.json: observed limits and veto/gate state
- training.json: before and after metrics evaluated with the same protocol
- decisions.json: decision IDs, risk verdicts, outcomes and evidence links
- paper_trades.json: paper-only trades, decision links and R multiples
- shadow_learning.json: training events, weights and review status
- runtime.json: Windows paper monitor, heartbeat, read/write validation
- mt5_demo.json: demo connection status, never full account numbers or passwords

Example (for list datasets, replace data with a list of allowlisted dictionaries):

    {
      "verification": "VERIFIED",
      "provenance": {
        "source": "private Windows PAPER export / reviewed council journal",
        "verified_at": "2026-11-07T03:00:00Z",
        "method": "operator comparison with trusted audit and original journal"
      },
      "data": {}
    }

The data value is a list for agents, signals, decisions, paper_trades and shadow_learning; an object for all others. Training supports before and after numeric dictionaries with win_rate, avg_r, ece, brier, sample_count, conflict_rate and approval_rate. Compare baseline and trained weights on identical holdout windows before marking a training export verified.

Provenance is a declarative review marker, not cryptographic proof. Only a trusted exporter/auditor should produce verification=VERIFIED. This dashboard checks schema and allowlisted fields but cannot independently validate raw Windows logs. Never hand-label an unverified source as verified. Missing/unverified exports render empty states, not invented metrics.

Exports are limited to 2MB and 500 rows per list. Unknown fields are removed to avoid exposing private settings, passwords and full account identifiers.

## Runtime

Keep the evidence folder read-only and off public hosting; serve owner pages and owner API on the same origin behind HTTPS. The /traders view is a separate read-only market-context UI, not a signed-in per-user trading account. Its public market endpoint does not provide /sam access.

Refresh re-reads verified exports. History switches to a filterable, sortable PAPER table. Neither action affects training, the Windows service, the MT5 connector or execution.

## Tests

Run:
  python -m pytest -q tests/test_owner_dashboard.py tests/test_public_website.py
  python -m pytest -q
  node --check app/owner_ui/owner.js

Work in an isolated worktree and venv. Do not merge Council evidence auditor PR #103 until its journal schema and Windows persistence evidence are reviewed.
