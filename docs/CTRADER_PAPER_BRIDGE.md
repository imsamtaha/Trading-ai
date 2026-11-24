# cTrader demo bridge for ATLAS PAPER

Ubuntu runs the read-only cTrader Open API session and the ATLAS PAPER worker in one process. cTrader supplies closed candles and timestamped bid/ask quotes. ATLAS uses its existing strategy, Senior Risk, Council, Executive, local ledger, and settled-outcome calibration. The worker uses a configurable simulated starting balance and stores its records in `data/ctrader/`.

The nine-seat Council library is available for separate PAPER review. Its independent seat evidence and Chair verdicts are required before its retrospective evaluator can measure those decisions. The bridge forwards data to the implemented PAPER Council.

## Connect the demo account

1. Register an approved application in the [cTrader Open API portal](https://openapi.ctrader.com/). Authorize the intended demo account with the `accounts` permission. [cTrader authorization instructions](https://help.ctrader.com/open-api/account-authentication/)
2. Use the Ubuntu host’s private environment configuration for `ATLAS_CTRADER_CLIENT_ID`, `ATLAS_CTRADER_CLIENT_SECRET`, `ATLAS_CTRADER_ACCESS_TOKEN`, and the platform login in `ATLAS_CTRADER_DEMO_LOGIN`.
3. Set `ATLAS_BROKER_PROVIDER=ctrader`, `ATLAS_LIVE_TRADING=false`, and `ATLAS_DASHBOARD_ONLY=true`. Keep the host’s `data/` directory on persistent storage. Configure outbound TLS to `demo.ctraderapi.com:5036`.

Run these commands from the Trading-ai checkout.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.run_ctrader_paper --check --symbols XAUUSD
python -m scripts.run_ctrader_paper --once --symbols XAUUSD
python -m scripts.run_ctrader_paper --symbols XAUUSD
```

Use exact cTrader symbol names from the authorized demo account. The check verifies account access, candle retrieval, and a current two-sided quote. An inactive market can supply historical candles while the quote check waits for a current bid and ask. The worker closes its cTrader connection between cycles. Run one worker per state directory and use a separate directory for a different demo account.

The owner account panel can use the same demo credentials on the private ATLAS API host. It shows the broker account separately from simulated PAPER balances.

## Start training

The worker writes settled PAPER evidence to `data/ctrader/council_training.jsonl` and refreshes `data/ctrader/council_profile.json`. The existing calibration rules hold weights at baseline until the minimum sample count. Shadow Learning reviews the same settled PAPER ledger by default. For supervised research, export a separate chronological candle CSV and run the existing scikit-learn trainer with a local MLflow registry.

```sh
python -m scripts.run_ctrader_paper --symbols XAUUSD --interval 15m --candles 500 \
  --export-candles data/ctrader/XAUUSD_M15.csv
python -m atlas_training.train_agent --agent trend --csv data/ctrader/XAUUSD_M15.csv \
  --mlflow-uri http://127.0.0.1:5000 --no-auto-promote \
  --council-report data/ctrader/council_training_review.json
```

Install `requirements-training.txt` and start MLflow before the second command. [ATLAS offline MLflow guide](council/INDEX.md#offline-mlflow-research)

## Use MT5 as the optional provider

On the Windows MT5 host, use its existing private account configuration, set `ATLAS_BROKER_PROVIDER=mt5` and `ATLAS_MT5_CONNECTIONS_PAUSED=false`, and use the [MT5 PAPER launcher](../README_MT5.md). The private owner view reads its optional display identity from `ATLAS_MT5_WORKSPACE_EMAIL`. Keep that identity and the MT5 credentials on the authorized host.
