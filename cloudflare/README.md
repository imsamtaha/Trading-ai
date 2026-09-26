# ATLAS Subscriber Dashboard — Cloudflare Launch

This setup exposes the ATLAS **read-only subscriber dashboard** while keeping MT5/API execution routes inaccessible from the public origin.

## Architecture

```text
Trader
  |
  v
/subscribe (public)
  |
  v
Hosted checkout / access approval
  |
  v
Cloudflare Access (email OTP)
  |
  v
/dashboard (private subscriber view)
  |
  v
Cloudflare Tunnel
  |
  v
127.0.0.1:8000
  |
  v
ATLAS + REAL MT5 telemetry
```

## 1. Start ATLAS locally

```powershell
cd "$HOME\Trading-ai"
.\.venv\Scripts\Activate.ps1
$env:ATLAS_DASHBOARD_ONLY="true"
$env:ATLAS_LIVE_TRADING="false"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify:

```text
http://127.0.0.1:8000/subscribe
http://127.0.0.1:8000/dashboard
```

The public origin remains read-only when `ATLAS_DASHBOARD_ONLY=true`.

## 2. Temporary public link

Run on the same Windows machine:

```powershell
cloudflared tunnel --config NUL --protocol http2 --url http://localhost:8000
```

Cloudflare prints a temporary `https://<random>.trycloudflare.com` hostname. Your temporary links become:

```text
https://<random>.trycloudflare.com/subscribe
https://<random>.trycloudflare.com/dashboard
```

Use Quick Tunnels for testing, not the paid production service. The `NUL`
config is intentional on Windows: it prevents a local named-tunnel config from
being auto-loaded into the temporary tunnel.

## 3. Stable production hostname

Create a named Cloudflare Tunnel and point a domain such as:

```text
atlas.yourdomain.com
```

to:

```text
http://localhost:8000
```

For `justai-atlas.online`, the DNS record must be a proxied CNAME to the
named tunnel target, normally:

```text
justai-atlas.online CNAME <tunnel-uuid>.cfargotunnel.com
```

Remove any A or AAAA records for the hostname that point at Cloudflare-owned
edge IPs. Those records cause Cloudflare Error 1000 ("DNS points to
prohibited IP") before the request can reach ATLAS. After the named tunnel
credentials are installed locally, create or repair the route with:

```powershell
cloudflared tunnel route dns atlas justai-atlas.online
```

Run the repository launcher in stable mode only after the credentials file
exists:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas_public.ps1 -TunnelMode named -TunnelName atlas
```

Recommended public URLs:

```text
https://atlas.yourdomain.com/subscribe
https://atlas.yourdomain.com/dashboard
```

## 4. Subscriber access

Keep `/subscribe` public. Protect `/dashboard*` with Cloudflare Access.

Create a **Self-hosted** Cloudflare Access application for:

```text
atlas.yourdomain.com/dashboard*
```

Enable email one-time PIN. Add paying subscriber email addresses to the Allow policy. Do not give subscribers MT5 credentials.

## 5. Payments

Configure a hosted payment page (recommended: Stripe Payment Link) and set:

```text
ATLAS_CHECKOUT_URL=https://your-hosted-checkout-link
ATLAS_SUBSCRIPTION_PRICE=$19/month
ATLAS_SUBSCRIPTION_TRIAL=7-day viewer trial
```

After payment, add the customer's email to Cloudflare Access. This can be automated later with a payment webhook + Cloudflare API; until then, manual approval is the safest launch workflow.

## 6. Real MT5 account

Keep these only on the private Windows worker:

```text
MT5_LOGIN=<real account>
MT5_PASSWORD=<private password>
MT5_SERVER=<broker server>
```

Start with:

```text
ATLAS_LIVE_TRADING=false
```

Confirm the dashboard reports `REAL` before enabling live execution. Public subscriber access remains read-only even if the private execution worker is later enabled.

## 7. Security checklist

- [ ] `justai-atlas.online` is a CNAME to `<tunnel-uuid>.cfargotunnel.com`.
- [ ] No A/AAAA record for `justai-atlas.online` points to a Cloudflare edge IP.
- [ ] `/subscribe` loads publicly.
- [ ] `/dashboard` requires Cloudflare Access authentication.
- [ ] `/dashboard/atlas` is reachable only through subscriber access.
- [ ] Account login is masked.
- [ ] `/mt5/test-order` returns 403 from the public origin.
- [ ] Broker credentials are not committed.
- [ ] `ATLAS_DASHBOARD_ONLY=true` is enabled for the public API process.
- [ ] Payment claims do not promise profit or guaranteed performance.
