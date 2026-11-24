# ATLAS training dashboard

Owner-only panel at /dashboard#training, refreshed every 30 seconds through GET /api/runtime/training. The route verifies the existing authenticated owner identity before reading data and returns private, no-store aggregates. No trading state, risk setting, or broker order is modified.

Sources: the local paper ledger, live Council profile, settled Council journal, shadow report, and a bounded tail of the signal journal. Raw trades, account identifiers, paths, tokens, evidence and free-text event reasons are not returned.

Weights compare against the reconstructed profile immediately before the current UTC date. Missing history appears as a dash. Weight is influence, not a probability. Lower Brier is better. Asset classifications use the monitor's canonical universe registry. Unknown instruments remain Other.

Selector readiness requires both the configured minimum of settled examples and distinct UTC entry dates. Meeting these minimums does not bypass purging, label variation, or evaluation gates and never activates live trading.

Rejection counts are recent sampled events, not unique opportunities or the daily total. The API reads at most 512 KiB and 1,000 event lines, with explicit sample timestamps and a stale indicator after 180 seconds without a current event. Missing sources are unknown, never silently zero.

R returns are risk-normalized paper results; spread is included, commissions/fees excluded. Reports are exploratory, not proof of 80% success.

Deployment: ops/deploy_atlas_web_preserving.py validates TypeScript, builds a unique isolated candidate, checks pages and assets on local port 8014, then promotes the candidate. Every previous production bundle is retained under a unique name and restored on failed health checks. No recursive cleanup runs.
