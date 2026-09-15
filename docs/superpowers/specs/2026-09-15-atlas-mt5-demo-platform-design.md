# ATLAS MT5 Demo Platform Integration Design

## Goal
Integrate ATLAS with the existing MT5 adapter as a demo-only market intelligence and execution-validation platform. ATLAS never holds client funds; the broker account remains external. This design does not enable real-money execution.

## Architecture
ATLAS UI -> Trading API -> Risk Gate -> Execution Service -> MT5 Adapter -> FxPro MT5 Demo

FxPro MT5 Demo -> MT5 Adapter -> account/quotes/positions -> ATLAS Dashboard

## Safety boundary
- Demo-only for this implementation.
- `ATLAS_LIVE_TRADING` must remain false.
- `MT5_REQUIRE_DEMO=true` is required for connected demo validation.
- Analysis availability and execution availability are separate states.
- Adding an asset never enables execution automatically.
- Every execution request must pass decision, risk, symbol, spread, and duplicate-order gates.

## Asset universe
Core classes:
- Metals: XAUUSD, XAGUSD
- Forex: EURUSD, GBPUSD, USDJPY
- Crypto: BTCUSD, ETHUSD, SOLUSD
- Indices: US500, NAS100, GER40
- Energy: USOIL, XNGUSD
- Stocks: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA

Broker symbols are resolved separately because FxPro/MT5 symbol names can differ from canonical ATLAS names.

## Components
1. Asset Registry: canonical symbols, class, risk profile, analysis/demo flags and broker aliases.
2. MT5 symbol resolver: discovers broker symbols and maps canonical symbols without guessing.
3. Demo Risk Gate: validates risk/reward, spread, exposure inputs, mandatory SL/TP and execution flags.
4. Duplicate-order guard: rejects repeated execution intents for the same canonical trade identity.
5. Portfolio sync: normalized account, positions, quote freshness and broker status for the dashboard.
6. Audit result: every request returns a deterministic approved/blocked reason.

## Success criteria
- Existing tests remain green.
- New registry tests cover all six asset classes.
- Unknown/unmapped broker symbols fail closed.
- Demo execution remains blocked unless the explicit demo policy is enabled.
- Live execution remains disabled.
- Duplicate execution requests are rejected.
- Dashboard-facing snapshot exposes broker connection, account summary, positions and asset mapping status without credentials.
