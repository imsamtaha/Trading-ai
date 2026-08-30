# ATLAS MT5 Worker

## Architecture

ATLAS runs its decision logic in Python. A persistent Windows worker owns the MetaTrader 5 terminal connection. Supabase is used as the control/audit plane.

`ATLAS -> Execution Gate -> MT5 Worker -> MetaTrader 5`

`MT5 Worker -> Supabase heartbeat/events`

## Windows setup

1. Install MetaTrader 5 and log into a **demo** account.
2. Clone this repository on the same Windows machine where MT5 is installed.
3. Create `.env` from `.env.mt5.example`.
4. Set `MT5_TERMINAL_PATH`, `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER`.
5. Set `SUPABASE_URL` to the project URL and `SUPABASE_SERVICE_ROLE_KEY` to a server-side secret. Never commit `.env` or this key.
6. Install dependencies: `pip install -r requirements.txt`.
7. Verify the terminal connection: `python scripts/verify_mt5.py`.
8. Start the worker: `python -m app.execution.worker`.

## Expected result

The worker should report `MT5 ONLINE` and periodically update `public.atlas_mt5_connections` in Supabase.

## Safety

`ATLAS_LIVE_TRADING=false` is required during integration. The worker only maintains the connection and heartbeat; trade decisions remain controlled by the ATLAS execution layer.

## Broker symbols

Use the exact symbols exposed by the broker. Common examples include `XAUUSD`, `EURUSD`, `XAGUSD`, and broker-specific variants with suffixes.
