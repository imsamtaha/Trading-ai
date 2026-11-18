# ATLAS × OmniRoute: private research gateway

Scope: OmniRoute supplies optional AI routing for private, non-executing ATLAS research summaries. It is not a broker, trading execution engine, Council voting agent, or source of verified market data.

## Windows installation and secrets

Existing installed gateway: OmniRoute 3.8.51 at localhost port 20128. ATLAS reads the owner's local OmniRoute API key from the Windows user profile at %LOCALAPPDATA%/OmniRoute/data/api-key.txt, or a configured key-file path. No key is included in this repository.

Never commit API keys, private .env files, tunnel credentials, local SQLite databases, or logs. No OmniRoute Cloudflare tunnel should be started by this integration.

## Owner-controlled configuration

Only after a reviewed deployment and resource/budget checks, set these values in the private Windows service environment:

    ATLAS_OMNIROUTE_ENABLED=true
    ATLAS_OMNIROUTE_BASE_URL=http://127.0.0.1:20128/v1
    ATLAS_OMNIROUTE_MODEL=auto
    ATLAS_DASHBOARD_ONLY=true
    ATLAS_LIVE_TRADING=false
    ATLAS_REAL_MONEY_EXECUTION=false

The gateway accepts only HTTP on 127.0.0.1 or localhost, port 20128, path /v1. Public addresses and tunnels are rejected. The feature defaults to disabled; deploying this branch does not silently enable it.

## Private owner endpoints

GET /sam/api/omniroute/status: owner-authenticated local model-catalog connectivity check, with no paid model generation. Returns READY, OMNIROUTE_DISABLED, LOCAL_OMNIROUTE_KEY_UNAVAILABLE, GATEWAY_UNREACHABLE or safety status without revealing secrets.

POST /sam/api/omniroute/research: owner-authenticated synthetic or non-sensitive market observations only. Summarizes supplied observations with uncertainty labels. It cannot generate broker orders, register models, change Council votes, or promote weights. Model inference can incur provider charges. Do not send credentials or account details.

Example POST JSON:

    {"symbol":"EURUSD","timeframe":"1h","observations":["Synthetic test: movement irregular.","No current data source supplied."]}

Research responses carry OMNIROUTE_LOCAL_LLM_UNVERIFIED and verified_market_data=false. They are not signals or investment advice.

## Validation and rollout

1. Keep ATLAS Paper Monitor, private backend, and read-only MT5 view healthy.
2. On the 8 GB Windows host, require approximately 1.2 GB RAM available before starting a heavy model gateway to avoid paging freezes.
3. Start only the locally installed OmniRoute process. Do not restart the public OmniRoute tunnel.
4. Confirm the loopback listener and owner-authenticated local status check. READY means a catalog responded, not that model inference was tested.
5. Run: python -m pytest -q tests/test_omniroute_gateway.py tests/test_omniroute_owner_api.py
6. Check GitHub CI and privacy before merging, deploying, or enabling the feature.
7. Keep all active Council weights, broker execution and real-money trading unchanged.

Default disabled until these checks pass. This integration neither alters local OmniRoute credentials nor starts a network-accessible service.