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
Whish Money request + manual access approval
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
cd "$HOME\\Trading-ai"
.\\.venv\\Scripts\\Activate.ps1
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
cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a temporary `https://<random>.trycloudflare.com` hostname. Your temporary links become:

```text
https://<random>.trycloudflare.com/subscribe
https://<random>.trycloudflare.com/dashboard
```

Use Quick Tunnels for testing, not the paid production service.

## 3. Stable production hostname

Create a named Cloudflare Tunnel and point a domain such as:

```text
atlas.yourdomain.com
```

to:

```text
http://localhost:8000
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

Enable email one-time PIN. Add only manually approved subscriber email addresses
to the Allow policy. Do not give subscribers MT5 credentials.

## 5. Whish Money requests

Set these on the private server:

```text
ATLAS_WHISH_ENABLED=true
ATLAS_WHISH_RECIPIENT=Samir Taha
ATLAS_WHISH_SUPPORT=+96176420910
ATLAS_WHISH_DB=data/whish_requests.sqlite3
```

A customer submits a request from `/subscribe`, then receives instructions to
pay with Whish Money. Reconcile the payment outside ATLAS and add the verified
email to Cloudflare Access. No automatic renewal, transfer confirmation, or
access activation is enabled.

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

- [ ] `/subscribe` loads publicly.
- [ ] `/dashboard` requires Cloudflare Access authentication.
- [ ] `/dashboard/atlas` is reachable only through subscriber access.
- [ ] Account login is masked.
- [ ] `/mt5/test-order` returns 403 from the public origin.
- [ ] Broker credentials are not committed.
- [ ] `ATLAS_DASHBOARD_ONLY=true` is enabled for the public API process.
- [ ] Whish requests are reconciled before dashboard access is approved.
- [ ] Payment claims do not promise profit or guaranteed performance.
