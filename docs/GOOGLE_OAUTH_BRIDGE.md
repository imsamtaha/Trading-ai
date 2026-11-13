# ATLAS Google OAuth Bridge (Termux)

This bridge connects ATLAS Right Hand to Gmail and Google Calendar with OAuth 2.0. Version 1 is read-only by design.

## Google Cloud setup

1. Create or select a Google Cloud project.
2. Enable **Gmail API** and **Google Calendar API**.
3. Configure the OAuth consent screen.
4. Create an **OAuth 2.0 Client ID** of type **Web application**.
5. Add this redirect URI exactly:

```text
http://127.0.0.1:8001/oauth/google/callback
```

Never commit the client secret or generated token file.

## Termux environment

```bash
cd ~/Trading-ai

export ATLAS_BRIDGE_SERVER_TOKEN="replace-with-a-private-random-token"
export ATLAS_GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
export ATLAS_GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
export ATLAS_GOOGLE_REDIRECT_URI="http://127.0.0.1:8001/oauth/google/callback"
export ATLAS_GOOGLE_TOKEN_PATH="$HOME/.atlas_google_token.json"

python -m uvicorn bridge.google_oauth_bridge:app --host 127.0.0.1 --port 8001
```

Check health:

```bash
curl http://127.0.0.1:8001/health
```

## Authorize Google

Request the authorization URL:

```bash
curl http://127.0.0.1:8001/oauth/google/start
```

Open the returned `authorization_url` in the browser on the same device, approve read-only Gmail and Calendar access, and Google will redirect to the local callback.

A successful callback returns:

```json
{"status":"connected"}
```

## Point ATLAS at the bridge

In the ATLAS API session:

```bash
export ATLAS_TOOL_BRIDGE_URL="http://127.0.0.1:8001"
export ATLAS_TOOL_BRIDGE_TOKEN="$ATLAS_BRIDGE_SERVER_TOKEN"
```

Restart the ATLAS API after setting these variables.

## Read tests

Gmail:

```bash
curl -X POST http://127.0.0.1:8001/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ATLAS_BRIDGE_SERVER_TOKEN" \
  -d '{"tool":"gmail.read","arguments":{"query":"newer_than:1d -in:spam -in:trash","max_results":5},"approved":false,"caller":"atlas-right-hand"}'
```

Calendar:

```bash
curl -X POST http://127.0.0.1:8001/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ATLAS_BRIDGE_SERVER_TOKEN" \
  -d '{"tool":"calendar.read","arguments":{"max_results":10},"approved":false,"caller":"atlas-right-hand"}'
```

## Security model

- OAuth scopes are read-only: `gmail.readonly` and `calendar.readonly`.
- Google credentials stay in Termux environment variables, not Git.
- OAuth tokens are stored locally with restrictive file permissions where supported.
- The bridge requires a bearer token when `ATLAS_BRIDGE_SERVER_TOKEN` is configured.
- `gmail.write` and `calendar.write` are not implemented in v1, even when `approved=true`.
- Keep the bridge bound to `127.0.0.1` unless a private authenticated deployment is intentionally configured.
