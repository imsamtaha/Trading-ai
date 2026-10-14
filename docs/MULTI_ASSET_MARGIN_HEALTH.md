# Multi-asset sizing and Risk Executive margin health

The latest requested policy is **20% of free margin and a 200% minimum margin
level**, replacing the earlier 30% proposal. This protects new entries. It does
not liquidate existing positions or change live-trading flags.

## Margin health

```text
Calculated Free Margin = Equity - Used Margin
Effective Free Margin = min(Calculated Free Margin, reported MT5 Free Margin)
Maximum Required Margin = Effective Free Margin × 0.20
Current Margin Level % = Equity / Used Margin × 100
Projected Equity = Equity - estimated opening spread cost
Projected Used Margin = Used Margin + Required Margin
Projected Margin Level % = Projected Equity / Projected Used Margin × 100
```

New entry is vetoed if required margin exceeds the maximum, current or projected
margin level is below 200%, or the required data is missing/malformed. Equality
at 20% and 200% is allowed. Zero used margin produces a null margin level rather
than Infinity. An account without free margin cannot add exposure. Projected
margin is conservatively additive; the engine does not assume hedging rebates.

Opening spread is reserved in projected equity, including the final native
entry check. This avoids approving a 200% projection that immediately becomes
199.8% because of spread. Estimates do not include unknown commissions, swaps,
future price movement or fill slippage and are not a guaranteed post-fill level.

## Asset specification table

These are **the user's USD paper assumptions**, not current FxPro specifications
or verified market spreads. Lot steps follow the supplied minimum-lot examples.
Actual broker constraints, currency conversion and margin calculations override
this table in broker mode; broker leverage is never inferred from these values.

| Paper asset | Units per lot | Assumed leverage | Minimum lot | Lot step | Assumed spread in price units |
| --- | ---: | ---: | ---: | ---: | ---: |
| XAUUSD | 100 | 1:100 | 0.01 | 0.01 | 0.30 |
| EURUSD | 100000 | 1:200 | 0.01 | 0.01 | 0.00015 |
| BTCUSD | 1 | 1:10 | 0.01 | 0.01 | 15.00 |
| SPX500 | 1 | 1:20 | 0.1 | 0.1 | 0.50 |

`MultiAssetRiskEngine` keeps lots and units separate:

```text
Units = Lots × Contract Size
Paper Notional = Units × Entry Price
Paper Required Margin = Paper Notional / Assumed Leverage
```

Lots are rounded **down** to the permitted step and capped by actual broker
maximum volume in broker mode. If the budget cannot afford the minimum lot, the
estimate is rejected; the minimum is never forced upward. The default risk
fraction is 0.01 (1%), subject to the existing per-trade ceiling. The execution
coordinator additionally caps it at the cash budget already approved by the
existing daily-loss, aggregate-risk and position-value policy.

Paper sizing conservatively reserves spread in stop-risk unless the caller
explicitly states that the entry price already includes spread. Broker sizing
requires an executable ask/bid entry and uses `order_calc_profit` for cash risk
and `order_calc_margin` for margin, both in account currency. Spread is not
added twice to the executable-entry-to-stop loss. It is separately estimated
for the projected equity check. Lot volume and contract size come from
`symbol_info`, supporting actual broker symbol suffixes and additional assets.
`notional_value` is in symbol quote currency and is not used as account-currency
margin evidence in broker mode.
Broker estimates reject stops inside the spread. At the native entry boundary,
rounded BUY stops must remain below fresh Bid and SELL stops above fresh Ask;
both quote prices must be positive and finite. These checks do not replace the
broker's additional stop-distance and trading constraints.

## Integration

- Root automatic execution obtains used/free margin from its fresh broker
  portfolio snapshot, builds native multi-asset sizing, then passes it to Risk
  Executive. Existing stop, portfolio-correlation and other risk vetoes remain.
- Risk Executive independently recomputes margin health from sizing evidence;
  an `APPROVED` flag or altered confidence cannot override failed checks.
- Execution service bounds submitted volume by the approved lots and retains
  cash-risk/stop bounds. MT5 checks native margin health before reservation and
  again after the final portfolio/account read, before `order_send`.
- Position closing stays separate. The divergent private broker remains
  fail-closed from the preceding council change. The legacy paper ledger still
  uses price units; this feature does not silently replace its positions with
  broker lots or assume a margin ledger it does not have.

A calculator result of `APPROVED` is a **sizing estimate**, not complete
portfolio approval or authorization to trade. Every result retains
`broker_execution_allowed: false`; only the separate guarded execution path can
use it after all other checks. No paid service or new dependency is required.

## Supplied gold example

With equity 100000, free margin 80000, entry 2650 and stop 2635:

- Lots: **0.65**; units: **65**.
- Stop risk: **975**; spread reserve: **19.50**; total estimated risk: **994.50**.
- Required margin: **1722.50**, below the **16000** margin cap.
- Used margin before entry: **20000**; projected margin level approximately
  **460.26%** after reserving spread.

These are computations under the supplied assumptions, not a current quote or
an actual order. Reproduce them with `python scripts/multi_asset_risk_demo.py`.

## Status and official references

The source is tested locally. No live order was sent and Windows deployment
remains pending while its Desktop Commander device is disconnected.

- [MetaTrader 5 Python: order_calc_margin](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py)
- [MetaTrader 5 Python: order_calc_profit](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
- [MetaTrader 5 Python: symbol_info](https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py)
- [MetaTrader 5: protective levels and spread](https://www.mql5.com/en/book/automation/symbols/symbols_spreads_levels)
