# ATLAS Right Hand Agent v2

ATLAS now exposes a general-purpose assistant routing layer in addition to the existing paper-only market decision engine.

## Specialist domains

- Executive Assistant: priorities, planning, summaries, follow-ups, project coordination.
- Research Intelligence: research, comparisons, source synthesis, reports.
- Tech Copilot: coding, debugging, architecture, tests, GitHub-oriented work.
- Automation Specialist: workflows, APIs, integrations, agent automation.
- Business Assistant: strategy, marketing, sales, positioning.
- ATLAS Market Intelligence: paper-only scalping context, multi-timeframe analysis, market/news context, and risk review.

## API

- `GET /agent/right-hand/capabilities`
- `POST /agent/right-hand/plan`

Example request:

```json
{
  "request": "Prepare my project priorities and review the latest ATLAS paper-trading status"
}
```

The planner returns the selected specialist, skills, suggested tools, execution mode, approval requirement, steps, and constraints.

## Safety and execution model

Read-only tools should be used first. Consequential external writes remain approval-gated. Market intelligence remains paper/demo only and the Right Hand Agent never routes live orders to MT5.

The existing deterministic ATLAS technical, structure, signal, risk, and multi-timeframe engines remain authoritative for market decisions.
