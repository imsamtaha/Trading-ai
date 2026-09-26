# Payment setup and display preferences

The dashboard, subscription page and manual Whish page now have Arabic/English
and light/dark controls. Preferences are stored in each browser. Market symbols,
provider names and original news headlines remain in their source language.

## Current payment model

ATLAS currently uses Whish Money manual payment intake only. Stripe prices are
not part of the active public subscription flow.

Active subscription methods:

- ATLAS Signals: 99 USD/month. ATLAS sends signals to the trader.
- ATLAS Execution: 149 USD/month. ATLAS executes approved signals only after
  account approval, safety-gate setup, and manual owner activation.

Payment collection alone is not a complete membership system. Access is still
manual review, and execution remains gated by ATLAS safety settings and account
authorization.

## Whish Money: manual requests, not a gateway integration

Whish publicly offers merchant Checkout at:
https://www.whish.money/corporate-solutions
Merchant credentials and the official integration contract are still required for
automated verification. No undocumented API or automatic payment approval is used.

For this ATLAS setup, the display contact is **Samir Taha — +961 76 420 910**.
Customers can send Whish payments to the configured phone number or scan the
configured QR image.

Set `ATLAS_WHISH_ENABLED=true` only after verifying this is the receiving
wallet and configuring:

```text
ATLAS_WHISH_RECIPIENT=Samir Taha
ATLAS_WHISH_SUPPORT=+96176420910
ATLAS_WHISH_PHONE=+96176420910
ATLAS_WHISH_QR_IMAGE_URL=https://your-public-qr-image-url.example/whish-qr.png
```

These values are intentionally public to customers; do not place secrets there.
ATLAS_WHISH_DB optionally specifies a private local SQLite path
(default data/whish_requests.sqlite3). Back it up and never serve or commit it.

/billing/whish/signals and /billing/whish/execution accept an email and persist
a reference with PENDING_REVIEW status. Repeat pending requests reuse the reference.
This is a request intake only: no payment is initiated, no receipt is accepted as
proof, no account access is granted, and no automatic renewal is promised.
Owner support must confirm the payment instructions and manually activate access.
There is no remote approval endpoint. Manual reconciliation and authenticated
membership activation remain to be integrated before public paid launch.

/billing/methods reports configuration presence only; it does not verify provider
connectivity, account eligibility, actual Price values or webhook delivery.
