# ATLAS Trading AI Demo

ATLAS is a deterministic multi-asset trading-analysis demo cockpit.

It shows live market-data analysis, ATLAS scoring, risk-gated decisions, and paper-trading candidate status.

> Safety boundary: this repository does **not** place live trades from the dashboard demo. The demo is for analysis, testing, and paper-trading validation only.

## Current demo features

- Live market-data dashboard
- ATLAS decision matrix
- Long/short scoring
- Risk vetoes
- Trade-gate candidate status
- Paper/demo mode
- Multi-asset watchlist:
  - XAUUSD
  - SILVER
  - GAS
  - EURUSD
  - SOLUSDT
  - XRPUSDT

## Quick start on Windows PowerShell

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="false"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Open:

```text
http://127.0.0.1:8010/dashboard
```

## Run tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_atlas_scoring_engine.py tests/test_atlas_pipeline_integration.py tests/test_atlas_trade_gate.py tests/test_atlas_dashboard_demo.py -v
```

Expected result:

```text
22 passed
```

## Let friends try it from your computer on the same Wi-Fi

1. Start the server on all local interfaces:

```powershell
.\.venv\Scripts\Activate.ps1
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="false"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

2. Find your local IP:

```powershell
ipconfig
```

Look for your Wi-Fi IPv4 address, for example:

```text
192.168.1.45
```

3. Friends on the same Wi-Fi open:

```text
http://192.168.1.45:8010/dashboard
```

Replace `192.168.1.45` with your real IPv4 address.

## Windows firewall note

If friends cannot open the page, Windows Firewall may be blocking Python/Uvicorn. Allow Python on Private networks only.

Do not expose this demo publicly with real credentials or trading permissions.

## Recommended sharing options

### Option A — GitHub sharing

Send friends the repository link and this command path:

```powershell
git clone https://github.com/imsamtaha/Trading-ai.git
cd Trading-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### Option B — Same Wi-Fi live demo

Run the server with:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Then share your local network URL:

```text
http://YOUR_IPV4_ADDRESS:8010/dashboard
```

### Option C — Screen-share demo

Use Zoom, Google Meet, Discord, or WhatsApp screen share and keep the app running locally.

This is the safest method while the system is still in validation mode.

## Production warning

Before any real-money use, ATLAS still requires:

- Historical backtesting
- Out-of-sample validation
- Persistent demo journaling
- Broker/MT5 read-only verification
- Explicit execution authorization layer
- Hard kill-switch and account-risk controls

The current version is a strong demo, not a licensed financial advisory or autonomous live-trading product.
