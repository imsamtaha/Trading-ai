# ATLAS Demo Access for Friends

This guide explains how to view the ATLAS dashboard demo safely.

## What this demo is

ATLAS is a market-analysis cockpit. It reads market data, analyzes multiple assets, scores direction, applies risk vetoes, and shows whether a paper-trading candidate would be allowed.

## What this demo is not

It is not a live trading system.

The demo does not place real MT5, broker, or exchange orders.

## Option 1 — View from Samir's computer on the same Wi-Fi

Ask Samir for the local demo link. It will look like this:

```text
http://192.168.1.45:8010/dashboard
```

Your device must be on the same Wi-Fi network.

If the page does not open, the likely causes are:

- You are not on the same Wi-Fi.
- Windows Firewall is blocking the server.
- The server is not currently running.
- The local IP address changed.

## Option 2 — Run your own local copy

Install Python, then run:

```powershell
git clone https://github.com/imsamtaha/Trading-ai.git
cd Trading-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ATLAS_LIVE_TRADING="false"
$env:ATLAS_DASHBOARD_ONLY="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010/dashboard
```

## What to look for in the dashboard

- Asset symbol
- Current price/data status
- ATLAS bias
- Long score
- Short score
- Conviction
- Risk vetoes
- Paper candidate status
- Execution disabled state

## Important risk note

This is an educational and technical demo. It should not be treated as financial advice or a guarantee of profitability.

Real-money trading requires more controls, including historical backtesting, out-of-sample validation, broker verification, execution authorization, and hard risk limits.
