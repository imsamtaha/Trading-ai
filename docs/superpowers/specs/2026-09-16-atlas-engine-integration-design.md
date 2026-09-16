# ATLAS Engine Integration Design

## Goal
Strengthen the existing ATLAS demo/paper-trading pipeline by integrating engine capabilities into the current Python architecture without a monorepo rewrite or duplicate engines.

## Architecture
Preserve the existing application boundaries and orchestrator. Treat existing analysis, intelligence, scoring, risk, execution, paper-trading, and performance modules as canonical. Add only missing engine capabilities behind focused interfaces and compose them through the existing decision path.

Target flow:

Market/Data -> Technical + Structure -> SEAL Intelligence -> Decision/Scoring -> Risk Gate -> Paper Execution -> Portfolio/Ledger -> Performance Feedback

News/event context contributes to intelligence/decision inputs but cannot execute orders directly.

## Constraints
- Fast-track integration; no monorepo migration.
- Do not require Redis Streams, Prisma, Docker Compose, or a Telegram rewrite for this milestone.
- Preserve current public/dashboard behavior.
- Preserve the risk gate and execution gate.
- Keep ATLAS_LIVE_TRADING=false and ATLAS_DASHBOARD_ONLY=true for this implementation milestone.
- No new engine may call broker order placement directly.
- Use existing modules rather than duplicating working engines.
- Tests must cover engine composition and verify that paper/demo execution remains the only permitted execution mode.

## Engine Map
1. Market/Data: existing app/data and connector market state.
2. Technical/Structure: existing app/analysis.
3. SEAL Intelligence: existing app/intelligence/seal_adapter.py plus context/confidence.
4. Decision/Scoring: existing app/intelligence/decision and app/intelligence/scoring.
5. News/Event: existing app/intelligence/events.py, ingestion.py, reaction.py; wire as bounded context rather than a direct executor.
6. Risk: existing app/risk; remains a hard pre-execution gate.
7. Execution: existing app/execution and orchestrator; demo/paper only in this milestone.
8. Portfolio/Ledger: add a focused portfolio aggregation capability over existing ledger/account/trade data if no canonical equivalent exists.
9. Performance/Learning: extend existing app/performance metrics into feedback summaries; no self-modifying trading parameters in this milestone.

## Success Criteria
- Existing tests remain green.
- New integration tests demonstrate deterministic multi-engine composition.
- Event/news context can influence analysis metadata without bypassing risk.
- Portfolio exposure can be summarized from current positions/trades.
- Performance feedback can summarize closed demo/paper outcomes without claiming future profitability.
- Live order placement remains disabled in the integrated branch.
