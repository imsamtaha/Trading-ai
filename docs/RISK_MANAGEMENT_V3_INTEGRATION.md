# ATLAS Risk Management V3 | education-only integration

Source: user-supplied `Risk Management tut V3.pdf` (40 pages). The original PDF was not copied to source control; this repository contains an original, paraphrased, page-indexed study reference at `knowledge/risk_management_v3.json`.

## Council integration

- `app/intelligence/risk_reference.py` provides a read-only reference manifest and topic lookup functions.
- `app/intelligence/council.py` includes `risk_education_reference` in each Council package.
- Risk decisions remain the existing deterministic Senior Risk results. The reference cannot vote, modify thresholds, or override a rejection.
- PAPER calibration and broker-isolation rules are unchanged.

## Studying the PDF

- Pages 1-14: trading vocabulary and market structure.
- Pages 15-19: market dynamics and price action.
- Pages 20-24: candlestick interpretation.
- Pages 25-26: drawdown and recovery math.
- Pages 27-29: entry/invalidation/target (Trading Trident).
- Pages 29-32: risk/reward and win-rate relationships.
- Page 33: position sizing (illustrative calculations).
- Pages 34-35: leverage and margin risks.
- Pages 36-40: managing trades and discretionary exits.

## Source verification and policy

Some source claims, including a broad 90% trader-loss figure, are not independently verified. The guide's illustrative leverage, discretionary stop-loss practices, and risk-per-trade percentages must **not** be substituted for ATLAS safeguards. Recalculate any sample arithmetic before using it in a study exercise. This integration does not change broker access, Paper simulation settings, or protected risk limits.

## Telegram

A separate repository, `imsamtaha/Just-AI-telegram-bot`, has a matching reference index and `/risk` command. Changes are source-code updates only until the bot runtime is redeployed with its own credentials. Neither repository embeds the original PDF bytes or a public download link.
