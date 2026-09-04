# ATLAS Subscriber Launch

This launch path exposes the subscriber-facing ATLAS dashboard while keeping live order execution disabled.

## Safety defaults

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- Public access is read-only.
- MT5 credentials stay private on the Windows worker and must never be committed.
- The bundled Stripe URL is sandbox/test mode only.

## One-command Windows launch

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas_public.ps1
```

The launcher:

1. verifies `.venv\Scripts\python.exe` exists,
2. verifies `cloudflared` is installed,
3. forces live trading off,
4. starts FastAPI on `127.0.0.1:8000`,
5. verifies `/health`,
6. configures the ATLAS Stripe sandbox subscription checkout,
7. starts a Cloudflare Quick Tunnel.

Cloudflare will print a URL similar to:

```text
https://example.trycloudflare.com
```

Use:

```text
https://example.trycloudflare.com/subscribe
https://example.trycloudflare.com/dashboard
```

## Install Cloudflared

If the launcher reports that `cloudflared` is missing, run:

```powershell
winget install --id Cloudflare.cloudflared
```

Close and reopen PowerShell, then verify:

```powershell
cloudflared --version
```

## Stripe sandbox

Current sandbox configuration:

- Product: `ATLAS Subscriber Access`
- Price: `$19/month`
- Trial: `7 days`
- Checkout mode: Stripe-hosted subscription checkout
- Environment: sandbox/test

The sandbox Payment Link is configured through `ATLAS_CHECKOUT_URL`. Test mode cannot collect live funds.

## Production conversion

Do not switch payments or trading execution to live at the same time.

Recommended sequence:

1. validate `/subscribe`, Checkout, and `/dashboard` end-to-end in sandbox,
2. replace the Quick Tunnel with a named Cloudflare Tunnel and stable domain,
3. protect `/dashboard*` with Cloudflare Access,
4. create a live Stripe product/price/payment link only when commercial settings are approved,
5. replace `ATLAS_CHECKOUT_URL` with the live Payment Link,
6. keep `ATLAS_LIVE_TRADING=false` until the private execution system has separately passed broker/risk validation.

Subscriber access remains observational and must not expose broker credentials or execution endpoints.
