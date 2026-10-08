# ATLAS MT5 Execution

ATLAS is split into three layers:

1. `app/intelligence/decision/engine.py` — determines BUY / SELL / WAIT and confidence/risk.
2. `app/execution/atlas.py` — enforces execution policy before an order can reach MT5.
3. `app/execution/mt5.py` — broker/data adapter using the official Python MetaTrader 5 package.

## Operating modes

### Safe mode (default)

`ATLAS_LIVE_TRADING` is not `true`, so orders are returned as `DRY_RUN` and are not submitted.

### Live mode

Only enable this on a dedicated Windows machine where the MT5 desktop terminal is installed, logged in, connected to the intended account, and trading is explicitly permitted.

Set:

```env
ATLAS_LIVE_TRADING=true
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=Broker-Server
MT5_TERMINAL_PATH=C:\\Program Files\\MetaTrader 5\\terminal64.exe
MT5_MAGIC=260830
MT5_DEVIATION=20
```

Do not commit `.env` or broker credentials.

## Important symbol note

Broker symbols vary. ATLAS should use the exact symbol names exposed by the connected MT5 account (for example, a broker may use `XAUUSD`, `XAUUSDm`, or another suffix). Configure symbol mappings separately rather than assuming Yahoo/Binance names are valid MT5 symbols.
