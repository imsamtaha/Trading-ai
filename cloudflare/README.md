# ATLAS Dashboard — Cloudflare Sharing

This setup exposes the ATLAS **read-only dashboard** to approved friends while keeping the MT5/API execution routes inaccessible from the public origin.

## Architecture

```text
Friends
  |
  v
Cloudflare Access (email OTP)
  |
  v
Cloudflare Tunnel
  |
  v
127.0.0.1:8000
  |
  v
ATLAS Dashboard
  |
  v
FxPro MT5 Demo
```

## 1. Local ATLAS configuration

Run ATLAS locally first:

```powershell
cd "$HOME\Trading-ai"
.\.venv\Scripts\Activate.ps1
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/dashboard` and verify the dashboard works.

`ATLAS_DASHBOARD_ONLY=true` blocks the market, analysis, MT5, and performance API routes at the FastAPI origin. Only the dashboard and health/documentation endpoints remain reachable.

## 2. Cloudflare Quick Tunnel — temporary demo

For a short test/demo, install `cloudflared` and run:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a temporary `trycloudflare.com` address. Share that address only for testing. Quick Tunnels are intended for development/testing, not production.

## 3. Production-style named tunnel

Use a Cloudflare-managed domain for a stable hostname such as:

```text
atlas.example.com
```

In Cloudflare:

1. Open **Networking → Tunnels**.
2. Create a tunnel named `atlas-dashboard`.
3. Add a published application route.
4. Set the hostname to `atlas.example.com`.
5. Set the service URL to `http://localhost:8000`.
6. Install/run `cloudflared` on the same Windows machine.

Do not commit tunnel credentials, tokens, certificates, or API keys to this repository.

## 4. Cloudflare Access

Protect the hostname before sharing it:

1. Open **Zero Trust → Access controls → Applications**.
2. Create a **Self-hosted** application.
3. Add the public hostname used by the tunnel.
4. Create an **Allow** policy containing only the email addresses of approved users.
5. Enable **One-time PIN** authentication for simple email-based login.
6. Test with one friend before adding additional users.

## 5. Security rules

Keep these settings:

```text
ATLAS_LIVE_TRADING=false
ATLAS_DASHBOARD_ONLY=true
```

Never share:

- MT5 username/password
- Supabase service-role key
- GitHub tokens
- Windows credentials
- `.env` files
- Cloudflare tunnel tokens

The dashboard is for observation and analysis. It does not provide friends with MT5 execution access.

## 6. Windows service option

For a persistent setup, Cloudflare supports running `cloudflared` as a Windows service. Configure the tunnel first, then install the service from an elevated terminal using the command provided by the Cloudflare dashboard.

## 7. Verification checklist

Before sharing the hostname:

- [ ] ATLAS starts successfully.
- [ ] `/dashboard` loads locally.
- [ ] MT5 remains connected to the demo account.
- [ ] `ATLAS_LIVE_TRADING=false`.
- [ ] `ATLAS_DASHBOARD_ONLY=true`.
- [ ] `/mt5/test-order` returns `403` locally.
- [ ] Cloudflare Access allows only approved emails.
- [ ] Friends can view the dashboard but cannot reach execution routes.
