# ATLAS Subscriber Launch

ATLAS is launched as a read-only intelligence dashboard by default. Live MT5
execution remains disabled until it separately passes documented risk gates.

## Safety defaults

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- The public dashboard contains no MT5 credentials or order controls.
- The Wall Street board labels provider data as delayed until a data licence
  explicitly grants real-time display rights.
- Payments use Whish Money request intake with manual review only.

## Commercial plans

| Plan | Price | Trial | Includes |
| --- | ---: | ---: | --- |
| ATLAS Reader | $49/month | 3 days | Read-only MT5 cockpit, Wall Street board, financial news, demo reports |
| ATLAS Pro Reader | $99/month | 3 days | Reader plus expanded market matrix, priority briefings, advanced risk reports |

Customers submit a Whish Money payment request. ATLAS does not collect card
details, initiate transfers, or activate access automatically.

## Required production settings

Set these only in the private deployment environment:

```text
ATLAS_FINNHUB_API_KEY=
ATLAS_WHISH_ENABLED=true
ATLAS_WHISH_RECIPIENT=Samir Taha
ATLAS_WHISH_SUPPORT=+96176420910
ATLAS_WHISH_DB=data/whish_requests.sqlite3
ATLAS_APP_URL=https://your-domain.example
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Verify the receiving Whish wallet and support number before public launch.
A request has `PENDING_REVIEW` status until you manually reconcile the
transfer and grant subscriber access.

## Windows demo launch

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\start_atlas_public.ps1
```

After the local health check succeeds, validate:

```text
/subscribe
/billing/methods
/dashboard
/dashboard/markets
/mt5/cockpit-state
```

## Execution readiness

Twenty to thirty demo executions validate wiring only. Keep
`ATLAS_LIVE_TRADING=false` until the risk review confirms order reconciliation,
daily-loss stops, a working kill switch, and a sufficiently broad forward-test
record across different market conditions.
